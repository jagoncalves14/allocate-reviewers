"""
Individual Developer Reviewer Rotation

This script assigns reviewers to individual developers
(rotate_devs_reviewers.py).

BUSINESS LOGIC:
1. Each developer can specify their own "Number of Reviewers" in the
   Google Sheet
   - Uses DEFAULT_REVIEWER_NUMBER as fallback if column is empty
   - Allows per-developer customization (e.g., Dev3 needs 2, Dev2 needs 3)

2. Experience-Based Assignment Rules:
   a) NON-EXPERIENCED DEVELOPERS:
      - Can ONLY be assigned experienced developers as reviewers
      - Cannot have non-experienced developers reviewing their code

   b) EXPERIENCED DEVELOPERS:
      - Must have at least 1 experienced developer as reviewer (mandatory)
      - Can have at most 1 non-experienced developer as additional reviewer
      - Example: Valid assignments: [Exp1, Exp2], [Exp1, NonExp1]
      - Example: Invalid assignment: [NonExp1, NonExp2]

3. Reviewer Selection Priority (in order):
   a) PREFERABLE REVIEWERS: Tries to assign reviewers from the
      developer's "Preferable Reviewers" list first
      - For non-experienced devs: only experienced devs from preferable list
   b) EXPERIENCED DEVELOPERS: Ensures EVERY developer gets at least 1
      experienced developer as a reviewer (mandatory requirement)
   c) EXPERIENCED DEVELOPERS: Fills remaining slots with experienced devs
   d) NON-EXPERIENCED DEVELOPERS: For experienced devs only, can add up to
      1 non-experienced dev if slots remain

4. Load Balancing & Smart Selection:
   - Never assigns a developer to review themselves
   - Tracks how many developers each reviewer is assigned to
   - Prioritizes reviewers with fewer assignments for fairness
   - Prevents scenarios where one reviewer gets 5 assignments while
     others get 0
   - Randomizes selection among equally loaded reviewers

5. Customization via Google Sheet:
   - "Number of Reviewers" column: How many reviewers this developer needs
   - "Preferable Reviewers" column: Comma-separated list of preferred names
   - Config sheet: Lists experienced developers

EXAMPLE 1 (Non-Experienced Developer):
Developer: Dev1 (non-experienced)
Number of Reviewers: 2
Preferable Reviewers: Dev2, Dev11
Experienced Devs: Dev2, Dev3, Dev4, Dev5

Allocation Process:
1. Try preferable: Dev2 (✓ experienced) → assigned
   (Dev11 skipped - not experienced)
2. Fill remaining: Dev3 (✓ experienced) → assigned
Result: Dev1 → reviewed by Dev2, Dev3

EXAMPLE 2 (Experienced Developer):
Developer: Dev2 (experienced)
Number of Reviewers: 2
Preferable Reviewers: Dev3, Dev1
Experienced Devs: Dev2, Dev3, Dev4, Dev5

Allocation Process:
1. Try preferable: Dev3 (✓ available) → assigned
2. Check experienced: Dev3 already assigned → requirement met ✓
3. Fill remaining: Can add 1 non-experienced (e.g., Dev1) → assigned
Result: Dev2 → reviewed by Dev3, Dev1

SCHEDULE:
- Called automatically by "Run All Review Rotations" workflow every Wednesday
  at 5:00 AM Finland Time (3:00 AM UTC)
- Only executes if 15 days have passed since last rotation
- Can also be triggered manually via "Run Developers Review Rotation" workflow
- Manual runs update existing column, scheduled runs create new column

NOTE: Uses the FIRST sheet/tab in the Google Sheet (index 0)
"""

import os
import sys
import random
import traceback
from typing import List, Set
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# pylint: next-line: disable=wrong-import-position
from dotenv import find_dotenv, load_dotenv
from lib.data_types import Developer, SelectableConfigure  # noqa: E402
from lib.env_constants import (  # noqa: E402
    EXPECTED_HEADERS_FOR_ALLOCATION,
)
from lib.utilities import (  # noqa: E402
    load_developers_from_sheet,
    get_remote_sheet,
    update_current_sprint_reviewers,
    format_and_resize_columns,
)

load_dotenv(find_dotenv())


def shuffle_and_get_the_most_available_names(
    available_names: Set[str], number_of_names: int, devs
) -> List[str]:
    if number_of_names == 0:
        return []
    names = list(available_names)

    if 0 == len(names) <= number_of_names:
        return names

    random.shuffle(names)
    # To select names that have the least assigned times.
    names.sort(
        key=lambda name: len(
            next(dev for dev in devs if dev.name == name).review_for
        ),
    )

    return names[0:number_of_names]


def allocate_reviewers(devs: List[Developer]) -> None:
    """
    Assign reviewers to input developers.
    The function mutate directly the input argument "devs".
    """
    # pylint: next-line: disable=import-outside-toplevel
    from lib.env_constants import EXPERIENCED_DEV_NAMES
    
    experienced_dev_names = set(EXPERIENCED_DEV_NAMES)

    all_dev_names = set((dev.name for dev in devs))
    valid_experienced_dev_names = set(
        (name for name in experienced_dev_names if name in all_dev_names)
    )
    
    non_experienced_dev_names = all_dev_names - valid_experienced_dev_names
    
    print(f"\n📊 Developer Classification:")
    print(f"   Names in FE Developers sheet: {sorted(all_dev_names)}")
    print(f"   Names from EXPERIENCED_DEV_NAMES env: {sorted(experienced_dev_names)}")
    print(f"   ✅ 👷 Matched (Experienced): {sorted(valid_experienced_dev_names)}")
    print(f"   ✅ 👨‍🎓 Non-experienced: {sorted(non_experienced_dev_names)}")
    
    # Show mismatches
    unmatched_from_config = experienced_dev_names - all_dev_names
    if unmatched_from_config:
        print(f"\n⚠️  WARNING: These names from Config don't match any developer:")
        for name in sorted(unmatched_from_config):
            print(f"      '{name}' (length: {len(name)}, repr: {repr(name)})")
    
    print(f"   Total: {len(all_dev_names)} developers\n")

    # To process devs with preferable_reviewer_names first.
    devs.sort(key=lambda dev: dev.preferable_reviewer_names, reverse=True)

    for dev in devs:
        chosen_reviewer_names: Set[str] = set()
        reviewer_number = min(dev.reviewer_number, len(all_dev_names) - 1)
        is_experienced_dev = dev.name in valid_experienced_dev_names
        
        exp_label = "👷 Experienced" if is_experienced_dev else "👨‍🎓 Non-experienced"
        print(f"🔄 Processing {dev.name} ({exp_label}, needs {reviewer_number} reviewers)")
        
        # Track non-experienced devs for filtering
        current_non_experienced = all_dev_names - valid_experienced_dev_names

        def selectable_number_getter() -> int:
            return max(reviewer_number - len(chosen_reviewer_names), 0)

        def experienced_reviewer_number_getter() -> int:
            # Check if we already have an experienced reviewer
            has_experienced = any(
                name in valid_experienced_dev_names
                for name in chosen_reviewer_names
            )
            if has_experienced:
                return 0
            # EVERYONE must have at least 1 experienced reviewer
            return 1

        def non_experienced_pool_getter() -> int:
            """
            Get number of slots to fill from non-experienced pool.
            - Non-experienced devs: NEVER (return 0)
            - Experienced devs: at most 1 non-experienced reviewer
            """
            if not is_experienced_dev:
                # Non-experienced devs can ONLY have experienced reviewers
                return 0

            # Count how many non-experienced reviewers already assigned
            non_experienced_count = sum(
                1 for name in chosen_reviewer_names
                if name in current_non_experienced
            )

            # Check if we have remaining slots
            remaining_slots = reviewer_number - len(chosen_reviewer_names)

            # Can add at most 1 non-experienced, and only if we have space
            if non_experienced_count == 0 and remaining_slots > 0:
                return min(1, remaining_slots)
            return 0

        # Build the selection pipeline
        # For non-experienced devs: preferable must also be experienced
        preferable_pool = (
            dev.preferable_reviewer_names & valid_experienced_dev_names
            if not is_experienced_dev
            else dev.preferable_reviewer_names
        )
        
        if not is_experienced_dev and dev.preferable_reviewer_names:
            filtered_out = dev.preferable_reviewer_names - valid_experienced_dev_names
            if filtered_out:
                print(f"   ⚠️  Filtered non-experienced from preferable: {filtered_out}")

        configures = [
            # Phase 1: Try preferable reviewers first
            SelectableConfigure(
                names=preferable_pool,
                number_getter=selectable_number_getter,
            ),
            # Phase 2: Ensure at least 1 experienced reviewer (mandatory)
            SelectableConfigure(
                names=valid_experienced_dev_names,
                number_getter=experienced_reviewer_number_getter,
            ),
            # Phase 3: Fill remaining slots with experienced devs
            SelectableConfigure(
                names=valid_experienced_dev_names,
                number_getter=selectable_number_getter,
            ),
            # Phase 4: For exp. devs only, can add up to 1 non-exp.
            SelectableConfigure(
                names=current_non_experienced,
                number_getter=non_experienced_pool_getter,
            ),
        ]

        for configure in configures:
            selectable_names = set(
                (
                    name
                    for name in configure.names
                    if name not in [dev.name, *chosen_reviewer_names]
                )
            )
            selectable_number = configure.number_getter()
            chosen_names = shuffle_and_get_the_most_available_names(
                selectable_names, selectable_number, devs
            )
            chosen_reviewer_names.update(chosen_names)

        reviewers = (dev for dev in devs if dev.name in chosen_reviewer_names)
        for reviewer in reviewers:
            dev.reviewer_names.add(reviewer.name)
            reviewer.review_for.add(dev.name)
        
        # Verify assignment correctness
        assigned_experienced = chosen_reviewer_names & valid_experienced_dev_names
        assigned_non_experienced = chosen_reviewer_names & non_experienced_dev_names
        
        print(f"   ✅ Assigned: {sorted(chosen_reviewer_names)}")
        print(f"      (Exp: {len(assigned_experienced)}, Non-exp: {len(assigned_non_experienced)})")
        
        # Validation warnings
        if not is_experienced_dev and assigned_non_experienced:
            print(f"   ⚠️  WARNING: Non-experienced dev has non-experienced reviewers!")
        if is_experienced_dev and len(assigned_non_experienced) > 1:
            print(f"   ⚠️  WARNING: Experienced dev has >1 non-experienced reviewers!")
        if not assigned_experienced:
            print(f"   ⚠️  WARNING: No experienced reviewer assigned!")
        print()


def write_reviewers_to_sheet(devs: List[Developer]) -> None:
    column_index = len(EXPECTED_HEADERS_FOR_ALLOCATION) + 1
    column_header = datetime.now().strftime("%d-%m-%Y")
    new_column = [column_header]

    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(
            expected_headers=EXPECTED_HEADERS_FOR_ALLOCATION
        )
        for record in records:
            developer = next(
                dev for dev in devs if dev.name == record["Developer"]
            )
            reviewer_names = ", ".join(
                sorted(developer.reviewer_names)
            )
            new_column.append(reviewer_names)
        sheet.insert_cols([new_column], column_index)

        # Format and resize columns
        num_rows = len(records) + 1
        format_and_resize_columns(sheet, column_index, num_rows)


if __name__ == "__main__":
    try:
        # Load configuration from Config sheet
        from lib.config_loader import load_config_from_sheet
        from lib import env_constants

        default_reviewer_number, exp_dev_names = (
            load_config_from_sheet()
        )
        env_constants.DEFAULT_REVIEWER_NUMBER = default_reviewer_number
        env_constants.EXPERIENCED_DEV_NAMES = exp_dev_names

        developers = load_developers_from_sheet(
            EXPECTED_HEADERS_FOR_ALLOCATION
        )
        allocate_reviewers(developers)

        # Manual runs update existing column, scheduled runs create new column
        is_manual = os.environ.get("MANUAL_RUN", "").lower() == "true"
        if is_manual:
            print("Manual run: Updating current sprint column")
            update_current_sprint_reviewers(
                EXPECTED_HEADERS_FOR_ALLOCATION, developers
            )
        else:
            print("Scheduled run: Creating new sprint column")
            write_reviewers_to_sheet(developers)
    except Exception as exc:
        print(f"\n❌ Error during Individual Developers rotation: {exc}")
        traceback.print_exc()
        raise  # Re-raise to ensure workflow fails
