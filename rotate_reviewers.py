"""
Allocate and Rotate Reviewers

FE DEVS ALLOCATION (allocate_reviewers.py):
- Randomly assigns experienced developers as reviewers to individual developers
- Each developer gets a specified number of reviewers
- At least one reviewer must be an experienced developer
- Runs every 15 days or manually

TEAMS ROTATION (this file - rotate_reviewers.py):
- Assigns reviewers to teams based on team composition
- Each team can specify "Number of Reviewers" in the sheet
- Uses DEFAULT_REVIEWER_NUMBER as fallback if column is empty
- Just like FE Devs, each team can have a different number of reviewers

Assignment Logic (for team needing N reviewers):
1. If team has 0 members:
   → Assign N experienced developers (load-balanced)

2. If team has fewer members than N:
   → Use all team members as reviewers
   → Fill remaining slots with experienced devs (not from team,
     load-balanced)

3. If team has >= N members:
   → Select N members from the team (load-balanced)

Load Balancing:
- Tracks how many teams each developer is reviewing
- Prioritizes developers with fewer assignments for fairness
- Prevents scenarios where one dev reviews 5 teams while others review 0

Examples:
- Team needs 2 reviewers, has 0 members → 2 experienced devs
  (least assigned)
- Team needs 2 reviewers, has 1 member (Robert) → Robert +
  1 experienced dev (least assigned)
- Team needs 2 reviewers, has 3+ members → 2 random members from team
  (least assigned)
- Team needs 3 reviewers, has 5 members → 3 members from team
  (least assigned)

Runs every 15 days on Wednesdays at 5:00 AM Finland Time (3:00 AM UTC)
or manually via GitHub Actions.
"""

import traceback
from typing import List
from datetime import datetime

from utilities import (
    get_remote_sheet,
    write_exception_to_sheet,
    load_developers_from_sheet,
    column_number_to_letter,
    update_current_team_rotation,
)
from data_types import Developer
from env_constants import (
    EXPECTED_HEADERS_FOR_ROTATION,
    TEAM_HEADER,
)


def parse_team_developers(team_developers_str: str) -> set[str]:
    """Parse comma-separated team developers into a set of names"""
    if not team_developers_str:
        return set()
    return set(name.strip() for name in team_developers_str.split(","))


def assign_team_reviewers(teams: List[Developer]) -> None:
    """
    Assign reviewers to teams based on team composition with load balancing.

    Args:
        teams: List of teams (stored as Developer objects), each with
               reviewer_number attribute

    Logic for each team needing N reviewers:
    - If team has 0 members: assign N random experienced devs
    - If team has < N members: use all members + fill with experienced devs
    - If team has >= N members: select N members

    Load Balancing:
    - Tracks how many teams each developer is reviewing ACROSS ALL TEAMS
    - Prioritizes developers with fewer assignments for fairness
    """
    import random
    from env_constants import EXPERIENCED_DEV_NAMES

    # Get list of experienced developers
    experienced_devs = list(EXPERIENCED_DEV_NAMES)
    if not experienced_devs:
        raise ValueError("EXPERIENCED_DEV_NAMES must be configured")

    # Track assignments per developer for load balancing ACROSS ALL TEAMS
    assignment_count: dict[str, int] = {}

    def select_balanced(candidates: list[str], count: int) -> list[str]:
        """Select 'count' reviewers from candidates, balancing workload"""
        if count >= len(candidates):
            return candidates

        # Sort by assignment count (ascending), then randomize ties
        candidates_copy = candidates.copy()
        random.shuffle(candidates_copy)  # Randomize first
        candidates_copy.sort(
            key=lambda name: assignment_count.get(name, 0)
        )  # Then sort by load

        return candidates_copy[:count]

    # Process ALL teams together to maintain load balancing state
    for team in teams:
        team.reviewer_indexes = set()
        team.reviewer_names = set()

        # Get team's developers and required reviewer count
        team_members = list(team.preferable_reviewer_names)
        num_members = len(team_members)
        num_reviewers = team.reviewer_number

        if num_members == 0:
            # No team members → assign balanced experienced devs
            selected = select_balanced(experienced_devs, num_reviewers)
            team.reviewer_names.update(selected)
            # Track assignments
            for dev_name in selected:
                assignment_count[dev_name] = (
                    assignment_count.get(dev_name, 0) + 1
                )

        elif num_members < num_reviewers:
            # Fewer members than needed → use all + fill with experienced devs
            team.reviewer_names.update(team_members)
            # Track team member assignments
            for dev_name in team_members:
                assignment_count[dev_name] = (
                    assignment_count.get(dev_name, 0) + 1
                )

            # Get experienced devs not in this team
            eligible = [
                dev for dev in experienced_devs if dev not in team_members
            ]

            # Fill remaining slots with balanced selection
            remaining_slots = num_reviewers - num_members
            if eligible and remaining_slots > 0:
                selected = select_balanced(eligible, remaining_slots)
                team.reviewer_names.update(selected)
                # Track assignments
                for dev_name in selected:
                    assignment_count[dev_name] = (
                        assignment_count.get(dev_name, 0) + 1
                    )

        else:
            # Enough members → select balanced from team
            selected = select_balanced(team_members, num_reviewers)
            team.reviewer_names.update(selected)
            # Track assignments
            for dev_name in selected:
                assignment_count[dev_name] = (
                    assignment_count.get(dev_name, 0) + 1
                )


def write_reviewers_to_sheet(teams: List[Developer]) -> None:
    # For Teams, we don't use the Indexes column anymore
    # Just insert the reviewers column after "Number of Reviewers"
    column_index = len(EXPECTED_HEADERS_FOR_ROTATION)
    column_header = datetime.now().strftime("%d-%m-%Y")
    new_column = [column_header]

    with get_remote_sheet("Teams") as sheet:
        records = sheet.get_all_records(
            expected_headers=EXPECTED_HEADERS_FOR_ROTATION
        )
        for record in records:
            team = next(t for t in teams if t.name == record[TEAM_HEADER])
            reviewer_names = ", ".join(sorted(team.reviewer_names))
            new_column.append(reviewer_names)

        sheet.insert_cols([new_column], column_index)

        # Apply styling: light blue for new, light grey for 5 old
        num_rows = len(records) + 1
        last_col = sheet.col_count

        try:
            # Style up to 5 older columns to the right (if they exist)
            max_old_cols_to_style = 5
            cols_to_style = min(
                max_old_cols_to_style, last_col - column_index
            )

            if cols_to_style > 0:
                for i in range(1, cols_to_style + 1):
                    col = column_index + i
                    col_letter = column_number_to_letter(col)
                    # Header: white bg, light grey text, not bold
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
                                    "red": 0.6,
                                    "green": 0.6,
                                    "blue": 0.6,
                                },
                                "bold": False,
                            },
                        },
                    )
                    # Data rows: light grey text, not bold
                    if num_rows > 1:
                        sheet.format(
                            f"{col_letter}2:{col_letter}{num_rows}",
                            {
                                "textFormat": {
                                    "foregroundColor": {
                                        "red": 0.6,
                                        "green": 0.6,
                                        "blue": 0.6,
                                    },
                                    "bold": False,
                                }
                            },
                        )

            # Apply light blue background to header of new column
            new_col_letter = column_number_to_letter(column_index)
            sheet.format(
                f"{new_col_letter}1",
                {
                    "backgroundColor": {
                        "red": 0.85,
                        "green": 0.92,
                        "blue": 1,
                    },
                    "textFormat": {
                        "foregroundColor": {"red": 0, "green": 0, "blue": 0},
                        "bold": True,
                    },
                },
            )
        except Exception as e:  # noqa: BLE001
            print(f"Warning: Could not apply background colors: {e}")


if __name__ == "__main__":
    import os
    from env_constants import (
        TEAM_DEVELOPERS_HEADER,
        TEAM_REVIEWER_NUMBER_HEADER,
        DEFAULT_REVIEWER_NUMBER,
    )

    try:
        teams = load_developers_from_sheet(
            EXPECTED_HEADERS_FOR_ROTATION,
            values_mapper=lambda record: Developer(
                name=record[TEAM_HEADER],
                reviewer_number=int(
                    record[TEAM_REVIEWER_NUMBER_HEADER]
                    or DEFAULT_REVIEWER_NUMBER
                ),
                # Store team developers in preferable_reviewer_names field
                preferable_reviewer_names=parse_team_developers(
                    record[TEAM_DEVELOPERS_HEADER]
                ),
            ),
            tab_name="Teams",
        )

        # Assign reviewers to ALL teams at once (maintains load balance)
        assign_team_reviewers(teams)

        # Check if this is a manual run
        is_manual_run = os.environ.get("MANUAL_RUN", "false") == "true"

        if is_manual_run:
            print("Manual run detected - updating current rotation")
            update_current_team_rotation(EXPECTED_HEADERS_FOR_ROTATION, teams)
        else:
            print("Scheduled run - creating new rotation")
            write_reviewers_to_sheet(teams)
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        write_exception_to_sheet(
            EXPECTED_HEADERS_FOR_ROTATION,
            str(exc) or str(type(exc)),
            tab_name="Teams",
        )
