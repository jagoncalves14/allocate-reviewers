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
from lib.data_types import Developer  # noqa: E402
from lib.env_constants import (  # noqa: E402
    EXPECTED_HEADERS_FOR_ALLOCATION,
)
from lib.utilities import (  # noqa: E402
    load_developers_from_sheet,
    get_remote_sheet,
    update_current_sprint_reviewers,
    format_and_resize_columns,
    increment_api_call_count,
    get_api_call_count,
    reset_api_call_count,
)

load_dotenv(find_dotenv())


def shuffle_and_get_the_most_available_names(
    available_names: Set[str], number_of_names: int, devs
) -> List[str]:
    """
    Select reviewers with load balancing - prioritize least assigned.

    Args:
        available_names: Set of available reviewer names
        number_of_names: Number of reviewers to select
        devs: List of all developers (to check current assignments)

    Returns:
        List of selected reviewer names (load-balanced and shuffled)
    """
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


def run_reviewer_allocation_algorithm(devs: List[Developer]) -> None:
    """
    Single attempt at assigning reviewers (internal function).
    
    Algorithm:
    1. Initial blind allocation with load balancing (respects preferable
       reviewers)
    2. Detect and fix experience-based rule violations
    3. Ensure non-experienced developers are assigned as reviewers

    The function mutates the input argument "devs" directly.
    """
    # pylint: next-line: disable=import-outside-toplevel
    from lib.env_constants import EXPERIENCED_DEV_NAMES

    experienced_dev_names = set(EXPERIENCED_DEV_NAMES)
    all_dev_names = set((dev.name for dev in devs))
    valid_experienced_dev_names = set(
        (name for name in experienced_dev_names if name in all_dev_names)
    )
    non_experienced_dev_names = all_dev_names - valid_experienced_dev_names

    print("\n📊 Developer Classification:")
    print(f"   Names in FE Developers sheet: {sorted(all_dev_names)}")
    print(
        f"   Names from EXPERIENCED_DEV_NAMES env: "
        f"{sorted(experienced_dev_names)}"
    )
    print(
        f"   ✅ 👷 Matched (Experienced): "
        f"{sorted(valid_experienced_dev_names)}"
    )
    print(f"   ✅ 👨‍🎓 Non-experienced: {sorted(non_experienced_dev_names)}")

    # Show mismatches
    unmatched_from_config = experienced_dev_names - all_dev_names
    if unmatched_from_config:
        print(
            "\n⚠️  WARNING: These names from Config don't match "
            "any developer:"
        )
        for name in sorted(unmatched_from_config):
            print(f"      '{name}' (length: {len(name)}, repr: {repr(name)})")

    print(f"   Total: {len(all_dev_names)} developers\n")

    # PHASE 1: Initial blind allocation with load balancing
    print("=" * 60)
    print("PHASE 1: Initial allocation (blind, with load balancing)")
    print("=" * 60)

    # Process devs with preferable_reviewer_names first
    devs.sort(
        key=lambda dev: len(dev.preferable_reviewer_names), reverse=True
    )

    for dev in devs:
        reviewer_number = min(dev.reviewer_number, len(all_dev_names) - 1)
        is_experienced = dev.name in valid_experienced_dev_names
        exp_label = (
            "👷 Experienced" if is_experienced else "👨‍🎓 Non-experienced"
        )

        print(
            f"🔄 {dev.name} ({exp_label}, needs {reviewer_number} reviewers)"
        )

        chosen_reviewer_names: Set[str] = set()

        # Step 1: Try preferable reviewers first
        if dev.preferable_reviewer_names:
            available_preferable = (
                dev.preferable_reviewer_names - {dev.name}
            )
            needed = reviewer_number - len(chosen_reviewer_names)
            if available_preferable and needed > 0:
                selected = shuffle_and_get_the_most_available_names(
                    available_preferable, needed, devs
                )
                chosen_reviewer_names.update(selected)
                print(f"   Preferable: {sorted(selected)}")

        # Step 2: Fill remaining slots from all available devs
        # (blind allocation)
        remaining_needed = reviewer_number - len(chosen_reviewer_names)
        if remaining_needed > 0:
            available = all_dev_names - chosen_reviewer_names - {dev.name}
            selected = shuffle_and_get_the_most_available_names(
                available, remaining_needed, devs
            )
            chosen_reviewer_names.update(selected)
            if selected:
                print(f"   Filled: {sorted(selected)}")

        # Apply assignments
        for reviewer_name in chosen_reviewer_names:
            reviewer = next(d for d in devs if d.name == reviewer_name)
            dev.reviewer_names.add(reviewer_name)
            reviewer.review_for.add(dev.name)

        print(f"   ✅ Total assigned: {sorted(chosen_reviewer_names)}\n")

    # PHASE 2: Fix experience-based rule violations
    print("\n" + "=" * 60)
    print("PHASE 2: Fix experience-based rule violations")
    print("=" * 60)

    for dev in devs:
        is_experienced = dev.name in valid_experienced_dev_names
        exp_label = "👷 Exp" if is_experienced else "👨‍🎓 Non-exp"

        # Recalculate assignments fresh for each developer
        assigned_exp = dev.reviewer_names & valid_experienced_dev_names
        assigned_non_exp = dev.reviewer_names & non_experienced_dev_names

        # Rule 1: Everyone must have at least 1 experienced reviewer
        if len(assigned_exp) == 0:
            msg = f"⚠️  {dev.name} ({exp_label}) has NO experienced reviewer!"
            print(msg)
            # Find available experienced devs
            available_exp = (
                valid_experienced_dev_names - dev.reviewer_names - {dev.name}
            )
            if available_exp:
                # Pick least loaded
                candidates = [d for d in devs if d.name in available_exp]
                candidates.sort(key=lambda d: len(d.review_for))
                replacement = candidates[0]

                # Recalculate assigned_non_exp in case it changed
                current_non_exp = (
                    dev.reviewer_names & non_experienced_dev_names
                )
                # If we need to make space, remove a non-exp reviewer
                if (
                    len(dev.reviewer_names) >= dev.reviewer_number
                    and current_non_exp
                ):
                    to_remove = list(current_non_exp)[0]
                    removed_dev = next(
                        d for d in devs if d.name == to_remove
                    )
                    dev.reviewer_names.remove(to_remove)
                    removed_dev.review_for.remove(dev.name)
                    print(f"   Removed: {to_remove}")

                # Add experienced reviewer
                dev.reviewer_names.add(replacement.name)
                replacement.review_for.add(dev.name)
                msg = f"   ✅ Added experienced reviewer: {replacement.name}\n"
                print(msg)

        # Rule 2: Non-experienced devs can ONLY have experienced reviewers
        # Recalculate to get current state
        current_non_exp_reviewers = (
            dev.reviewer_names & non_experienced_dev_names
        )
        if not is_experienced and len(current_non_exp_reviewers) > 0:
            msg = (
                f"⚠️  {dev.name} (Non-exp) has non-exp reviewers: "
                f"{current_non_exp_reviewers}"
            )
            print(msg)
            # Make a copy of the set to avoid modification during iteration
            for non_exp_name in list(current_non_exp_reviewers):
                # Check if it's still there (might have been removed)
                if non_exp_name not in dev.reviewer_names:
                    continue

                # Remove non-exp reviewer
                non_exp_dev = next(
                    d for d in devs if d.name == non_exp_name
                )
                dev.reviewer_names.discard(non_exp_name)
                non_exp_dev.review_for.discard(dev.name)
                print(f"   Removed: {non_exp_name}")

                # Replace with experienced reviewer
                available_exp = (
                    valid_experienced_dev_names
                    - dev.reviewer_names
                    - {dev.name}
                )
                if available_exp:
                    candidates = [
                        d for d in devs if d.name in available_exp
                    ]
                    candidates.sort(key=lambda d: len(d.review_for))
                    replacement = candidates[0]
                    dev.reviewer_names.add(replacement.name)
                    replacement.review_for.add(dev.name)
                    print(f"   ✅ Replaced with: {replacement.name}")
            print()

        # Rule 3: Experienced devs can have at most 1 non-experienced
        # reviewer
        # Recalculate to get current state
        current_non_exp_reviewers = (
            dev.reviewer_names & non_experienced_dev_names
        )
        if is_experienced and len(current_non_exp_reviewers) > 1:
            msg = (
                f"⚠️  {dev.name} (Exp) has "
                f"{len(current_non_exp_reviewers)} "
                f"non-exp reviewers: {current_non_exp_reviewers}"
            )
            print(msg)
            # Keep only 1 non-exp, remove the rest
            non_exp_list = list(current_non_exp_reviewers)
            to_keep = non_exp_list[0]
            to_remove = non_exp_list[1:]
            for non_exp_name in to_remove:
                non_exp_dev = next(
                    d for d in devs if d.name == non_exp_name
                )
                dev.reviewer_names.discard(non_exp_name)
                non_exp_dev.review_for.discard(dev.name)
                print(f"   Removed: {non_exp_name}")

                # Replace with experienced reviewer
                available_exp = (
                    valid_experienced_dev_names
                    - dev.reviewer_names
                    - {dev.name}
                )
                if available_exp:
                    candidates = [
                        d for d in devs if d.name in available_exp
                    ]
                    candidates.sort(key=lambda d: len(d.review_for))
                    replacement = candidates[0]
                    dev.reviewer_names.add(replacement.name)
                    replacement.review_for.add(dev.name)
                    print(f"   ✅ Replaced with: {replacement.name}")
            print(f"   Kept: {to_keep}\n")

    # PHASE 3: Ensure non-experienced developers are assigned as reviewers
    print("\n" + "=" * 60)
    print("PHASE 3: Ensure non-experienced devs are assigned as reviewers")
    print("=" * 60)

    unassigned_non_exp = [
        dev
        for dev in devs
        if dev.name in non_experienced_dev_names
        and len(dev.review_for) == 0
    ]

    if unassigned_non_exp:
        print(
            f"Found {len(unassigned_non_exp)} unassigned non-exp devs: "
            f"{[d.name for d in unassigned_non_exp]}\n"
        )

        # Sort by review_for load to prioritize least loaded
        unassigned_non_exp.sort(key=lambda d: len(d.review_for))

        for non_exp_dev in unassigned_non_exp:
            # Find experienced devs that can accept a non-experienced
            # reviewer
            candidates = []
            for exp_dev in devs:
                if exp_dev.name not in valid_experienced_dev_names:
                    continue
                if exp_dev.name == non_exp_dev.name:
                    continue

                # Count non-experienced reviewers this exp dev already has
                non_exp_count = sum(
                    1
                    for r_name in exp_dev.reviewer_names
                    if r_name in non_experienced_dev_names
                )

                # Check if they can accept another reviewer
                has_space = (
                    len(exp_dev.reviewer_names) < exp_dev.reviewer_number
                )
                has_no_non_exp = non_exp_count == 0

                if has_space and has_no_non_exp:
                    candidates.append(exp_dev)

            if candidates:
                # Sort by load (fewest review_for first) - maintain
                # balance!
                candidates.sort(key=lambda d: len(d.review_for))
                chosen = candidates[0]
                chosen.reviewer_names.add(non_exp_dev.name)
                non_exp_dev.review_for.add(chosen.name)
                msg = (
                    f"✅ Assigned {non_exp_dev.name} to review "
                    f"{chosen.name} (load: {len(chosen.review_for)})"
                )
                print(msg)
            else:
                msg = (
                    f"⚠️  Could not assign {non_exp_dev.name} - "
                    "no suitable candidates"
                )
                print(msg)
    else:
        print("✅ All non-experienced developers already assigned")

    # FINAL SUMMARY
    print("\n" + "=" * 60)
    print("FINAL ALLOCATION SUMMARY")
    print("=" * 60)
    for dev in devs:
        is_exp = dev.name in valid_experienced_dev_names
        exp_label = "👷 Exp" if is_exp else "👨‍🎓 Non-exp"
        assigned_exp = dev.reviewer_names & valid_experienced_dev_names
        assigned_non_exp = dev.reviewer_names & non_experienced_dev_names

        print(f"{dev.name} ({exp_label}): {sorted(dev.reviewer_names)}")
        print(
            f"  Reviewers: Exp={len(assigned_exp)}, "
            f"Non-exp={len(assigned_non_exp)}"
        )
        review_for_str = (
            sorted(dev.review_for) if dev.review_for else '(none)'
        )
        print(
            f"  Reviewing: {len(dev.review_for)} devs {review_for_str}"
        )
        print()


def allocate_reviewers(devs: List[Developer], max_retries: int = 10) -> None:
    """
    Assign reviewers to developers with retry mechanism.
    
    This function wraps run_reviewer_allocation_algorithm and retries with different
    random seeds if non-experienced developers are not assigned.
    
    Args:
        devs: List of developers to assign reviewers to
        max_retries: Maximum number of retry attempts (default: 10)
    """
    # pylint: next-line: disable=import-outside-toplevel
    from lib.env_constants import EXPERIENCED_DEV_NAMES
    from copy import deepcopy
    
    experienced_dev_names = set(EXPERIENCED_DEV_NAMES)
    all_dev_names = set((dev.name for dev in devs))
    valid_experienced_dev_names = set(
        (name for name in experienced_dev_names if name in all_dev_names)
    )
    non_experienced_dev_names = all_dev_names - valid_experienced_dev_names
    
    best_attempt = None
    best_assigned_count = 0
    
    for attempt in range(max_retries):
        # Create a deep copy for this attempt
        devs_copy = deepcopy(devs)
        
        # Try allocation
        try:
            run_reviewer_allocation_algorithm(devs_copy)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed with error: {e}")
            continue
        
        # Count how many non-exp devs are assigned
        assigned_count = sum(
            1 for dev in devs_copy
            if dev.name in non_experienced_dev_names
            and len(dev.review_for) > 0
        )
        
        # Track best attempt
        if assigned_count > best_assigned_count:
            best_assigned_count = assigned_count
            best_attempt = devs_copy
        
        # If all non-exp devs are assigned, we're done!
        if assigned_count == len(non_experienced_dev_names):
            print(f"\n✅ Success on attempt {attempt + 1}: All {assigned_count} "
                  f"non-exp devs assigned!")
            # Copy results back to original devs list
            for i, dev in enumerate(devs):
                dev.reviewer_names = devs_copy[i].reviewer_names
                dev.review_for = devs_copy[i].review_for
            return
        
        # Not perfect, try again with different random seed
        if attempt < max_retries - 1:
            # Change random seed for next attempt
            random.seed(attempt + 1000)
    
    # If we get here, use best attempt
    if best_attempt:
        print(f"\n⚠️  After {max_retries} attempts, best result: "
              f"{best_assigned_count}/{len(non_experienced_dev_names)} non-exp devs assigned")
        # Copy results back to original devs list
        for i, dev in enumerate(devs):
            dev.reviewer_names = best_attempt[i].reviewer_names
            dev.review_for = best_attempt[i].review_for
    else:
        raise RuntimeError(f"All {max_retries} allocation attempts failed!")


def write_reviewers_to_sheet(
    devs: List[Developer], sheet_name: str | None = None
) -> None:
    """
    Write reviewer assignments to a new column in the Google Sheet.

    Creates a new column with today's date as header and writes all
    reviewer assignments. Also applies formatting and resizing.

    Args:
        devs: List of developers with assigned reviewers
        sheet_name: Name of the Google Sheet file to write to.
            If None, uses first sheet from SHEET_NAMES environment variable.
    """
    column_index = len(EXPECTED_HEADERS_FOR_ALLOCATION) + 1
    column_header = datetime.now().strftime("%d-%m-%Y")
    new_column = [column_header]

    with get_remote_sheet(sheet_name=sheet_name) as sheet:
        records = sheet.get_all_records(
            expected_headers=EXPECTED_HEADERS_FOR_ALLOCATION
        )
        increment_api_call_count()  # 1 API call (get_all_records)
        for record in records:
            developer = next(
                (dev for dev in devs if dev.name == record["Developer"]), None
            )
            if developer is None:
                # Developer in sheet but not processed (removed from config?)
                dev_name = record["Developer"]
                print(
                    f"   ⚠️  WARNING: Developer '{dev_name}' in sheet "
                    f"but not in processed list - skipping"
                )
                new_column.append("")
            else:
                reviewer_names = ", ".join(sorted(developer.reviewer_names))
                new_column.append(reviewer_names)
        sheet.insert_cols([new_column], column_index)
        increment_api_call_count()  # 1 API call (insert_cols)

        # Format and resize columns
        num_rows = len(records) + 1
        format_and_resize_columns(sheet, column_index, num_rows)


if __name__ == "__main__":
    try:
        # Reset API call counter at start
        reset_api_call_count()
        
        # Load configuration from Config sheet
        from lib.config_loader import load_config_from_sheet
        from lib import env_constants

        default_reviewer_number, exp_dev_names = load_config_from_sheet()
        env_constants.DEFAULT_REVIEWER_NUMBER = default_reviewer_number
        env_constants.EXPERIENCED_DEV_NAMES = exp_dev_names

        developers = load_developers_from_sheet(EXPECTED_HEADERS_FOR_ALLOCATION)
        allocate_reviewers(developers)

        # Manual runs update existing column, scheduled runs create new column
        is_manual = os.environ.get("MANUAL_RUN", "").lower() == "true"
        if is_manual:
            print("Manual run: Updating current sprint column")
            update_current_sprint_reviewers(EXPECTED_HEADERS_FOR_ALLOCATION, developers)
        else:
            print("Scheduled run: Creating new sprint column")
            write_reviewers_to_sheet(developers)
        
        # Print total API calls at the end
        total_api_calls = get_api_call_count()
        print(f"\n📊 Total Google Sheets API calls: {total_api_calls}")
        
    except Exception as exc:
        print(f"\n❌ Error during Individual Developers rotation: {exc}")
        traceback.print_exc()
        raise  # Re-raise to ensure workflow fails
