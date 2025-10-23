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
- Runs every 15 days on Wednesdays at 5:00 AM Finland Time (3:00 AM UTC)
- Can be triggered manually via GitHub Actions
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

from dotenv import find_dotenv, load_dotenv

from lib.data_types import Developer, SelectableConfigure
from lib.env_constants import (
    EXPECTED_HEADERS_FOR_ALLOCATION,
)
from lib.utilities import (
    load_developers_from_sheet,
    get_remote_sheet,
    update_current_sprint_reviewers,
    column_number_to_letter,
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
    experienced_dev_names = set(
        os.environ.get("EXPERIENCED_DEV_NAMES", "").split(", ")
    )

    all_dev_names = set((dev.name for dev in devs))
    valid_experienced_dev_names = set(
        (name for name in experienced_dev_names if name in all_dev_names)
    )

    # To process devs with preferable_reviewer_names first.
    devs.sort(key=lambda dev: dev.preferable_reviewer_names, reverse=True)

    for dev in devs:
        chosen_reviewer_names: Set[str] = set()
        reviewer_number = min(dev.reviewer_number, len(all_dev_names) - 1)
        is_experienced_dev = dev.name in valid_experienced_dev_names

        # Non-experienced devs that can be selected as reviewers
        non_experienced_dev_names = all_dev_names - valid_experienced_dev_names

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
                if name in non_experienced_dev_names
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
                names=non_experienced_dev_names,
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

        # Style columns (optional - skip if rate limited)
        try:
            num_rows = len(records) + 1
            last_col = sheet.col_count

            # Apply light blue background ONLY to header of new column
            new_col_letter = column_number_to_letter(column_index)
            sheet.format(f"{new_col_letter}1", {
                "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 1},
                "textFormat": {
                    "foregroundColor": {"red": 0, "green": 0, "blue": 0},
                    "bold": True
                }
            })

            # Style older columns (if quota allows)
            if last_col > column_index:
                for col in range(
                    column_index + 1, min(last_col + 1, column_index + 6)
                ):
                    col_letter = column_number_to_letter(col)
                    sheet.format(
                        f"{col_letter}1",
                        {
                            "backgroundColor": {
                                "red": 1,
                                "green": 1,
                                "blue": 1,
                            },
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 0.8,
                                    "green": 0.8,
                                    "blue": 0.8,
                                },
                                "bold": False,
                            },
                        },
                    )
                    if num_rows > 1:
                        sheet.format(
                            f"{col_letter}2:{col_letter}{num_rows}",
                            {
                                "backgroundColor": {
                                    "red": 1,
                                    "green": 1,
                                    "blue": 1,
                                },
                                "textFormat": {
                                    "foregroundColor": {
                                        "red": 0.8,
                                        "green": 0.8,
                                        "blue": 0.8,
                                    },
                                    "bold": False,
                                },
                            },
                        )
        except Exception as e:
            print(f"Note: Styling skipped (quota or other issue): {e}")


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
