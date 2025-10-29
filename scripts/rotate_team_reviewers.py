"""
Team Reviewer Rotation

This script assigns reviewers to teams based on team composition.

TEAMS ROTATION (this file - rotate_team_reviewers.py):
- Assigns reviewers to teams based on team composition
- Each team can specify "Number of Reviewers" in the sheet
- Uses DEFAULT_REVIEWER_NUMBER as fallback if column is empty
- Just like individual developers, each team can have a different number
  of reviewers
- Uses SECOND sheet (index 1)

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
- Team needs 2 reviewers, has 1 member → the team member +
  1 experienced dev (least assigned)
- Team needs 2 reviewers, has 3+ members → 2 random members from team
  (least assigned)
- Team needs 3 reviewers, has 5 members → 3 members from team
  (least assigned)

SCHEDULE:
- Called automatically by "Run All Review Rotations" workflow every Wednesday
  at 5:00 AM Finland Time (3:00 AM UTC)
- Only executes if 15 days have passed since last rotation
- Can also be triggered manually via "Run Teams Review Rotation" workflow

NOTE: Uses the SECOND sheet/tab in the Google Sheet (index 1)
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.data_types import Developer  # noqa: E402
from lib.env_constants import (  # noqa: E402
    DEFAULT_REVIEWER_NUMBER,
    EXPECTED_HEADERS_FOR_ROTATION,
    TEAM_DEVELOPERS_HEADER,
    TEAM_HEADER,
    TEAM_REVIEWER_NUMBER_HEADER,
    TEAMS_SHEET,
)

# pylint: next-line: disable=wrong-import-position
from lib.utilities import (  # noqa: E402
    format_and_resize_columns,
    get_remote_sheet,
    load_developers_from_sheet,
    update_current_team_rotation,
)


def parse_team_developers(team_developers_str: str) -> set[str]:
    """Parse comma-separated team developers into a set of names"""
    if not team_developers_str:
        return set()
    return set(name.strip() for name in team_developers_str.split(","))


def assign_team_reviewers(
    teams: List[Developer], all_developers: List[str] | None = None
) -> None:
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
    # pylint: next-line: disable=import-outside-toplevel
    import random

    from lib.env_constants import UNEXPERIENCED_DEV_NAMES  # noqa: F811

    # Get list of experienced developers (INVERTED LOGIC)
    # Build from all team members plus provided all_developers minus unexperienced ones
    all_dev_names = set()
    for team in teams:
        all_dev_names.update(team.preferable_reviewer_names)

    # Add any explicitly provided developers
    if all_developers:
        all_dev_names.update(all_developers)

    unexperienced_dev_names = set(UNEXPERIENCED_DEV_NAMES)
    experienced_dev_names = all_dev_names - unexperienced_dev_names
    experienced_devs = list(experienced_dev_names)

    print(f"\n📊 Team Rotation Summary:")
    print(f"   Teams to process: {len(teams)}")
    print(f"   Experienced developers pool: {len(experienced_devs)}")
    print(f"   {sorted(experienced_devs)}\n")

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

        print(f"🔄 Processing Team: {team.name}")
        print(f"   Team members: {team_members if team_members else '(none)'}")
        print(f"   Needs: {num_reviewers} reviewers")

        if num_members == 0:
            # No team members → assign balanced experienced devs
            print(f"   Strategy: Team has no members → selecting from experienced devs")
            selected = select_balanced(experienced_devs, num_reviewers)
            team.reviewer_names.update(selected)
            # Track assignments
            for dev_name in selected:
                assignment_count[dev_name] = assignment_count.get(dev_name, 0) + 1
            print(f"   ✅ Assigned: {sorted(selected)}")

        elif num_members < num_reviewers:
            # Fewer members than needed → use all + fill with experienced devs
            print(
                f"   Strategy: Team has {num_members} members, needs {num_reviewers} → using all members + experienced devs"
            )
            team.reviewer_names.update(team_members)
            # Track team member assignments
            for dev_name in team_members:
                assignment_count[dev_name] = assignment_count.get(dev_name, 0) + 1

            # Get experienced devs not in this team
            eligible = [dev for dev in experienced_devs if dev not in team_members]

            # Fill remaining slots with balanced selection
            remaining_slots = num_reviewers - num_members
            if eligible and remaining_slots > 0:
                selected = select_balanced(eligible, remaining_slots)
                team.reviewer_names.update(selected)
                # Track assignments
                for dev_name in selected:
                    assignment_count[dev_name] = assignment_count.get(dev_name, 0) + 1
                print(f"   ✅ Assigned: {sorted(team_members)} + {sorted(selected)}")
            else:
                print(f"   ✅ Assigned: {sorted(team_members)}")

        else:
            # Enough members → select balanced from team
            print(
                f"   Strategy: Team has {num_members} members, needs {num_reviewers} → selecting from team"
            )
            selected = select_balanced(team_members, num_reviewers)
            team.reviewer_names.update(selected)
            # Track assignments
            for dev_name in selected:
                assignment_count[dev_name] = assignment_count.get(dev_name, 0) + 1
            print(f"   ✅ Assigned: {sorted(selected)}")

        print()

    # Show load balancing summary
    if assignment_count:
        print(f"📊 Load Balancing Summary:")
        print(f"   Total assignments: {sum(assignment_count.values())}")
        for dev, count in sorted(assignment_count.items(), key=lambda x: (-x[1], x[0])):
            print(f"   {dev}: {count} team(s)")
        print()


def write_reviewers_to_sheet(
    teams: List[Developer], sheet_name: str | None = None
) -> None:
    """
    Write team reviewer assignments to a new column in the Google Sheet.

    Creates a new column with today's date as header and writes all
    team reviewer assignments. Also applies formatting and resizing.

    Args:
        teams: List of teams with assigned reviewers
        sheet_name: Name of the Google Sheet file to write to.
            If None, uses first sheet from SHEET_NAMES environment variable.
    """
    # For Teams, we don't use the Indexes column anymore
    # Just insert the reviewers column after "Number of Reviewers"
    column_index = len(EXPECTED_HEADERS_FOR_ROTATION) + 1
    column_header = datetime.now().strftime("%d-%m-%Y")
    new_column = [column_header]

    with get_remote_sheet(TEAMS_SHEET, sheet_name=sheet_name) as sheet:
        records = sheet.get_all_records(expected_headers=EXPECTED_HEADERS_FOR_ROTATION)
        for record in records:
            team = next((t for t in teams if t.name == record[TEAM_HEADER]), None)
            if team is None:
                # Team in sheet but not processed (removed from config?)
                team_name = record[TEAM_HEADER]
                print(
                    f"   ⚠️  WARNING: Team '{team_name}' in sheet "
                    f"but not in processed list - skipping"
                )
                new_column.append("")
            else:
                reviewer_names = ", ".join(sorted(team.reviewer_names))
                new_column.append(reviewer_names)

        sheet.insert_cols([new_column], column_index)

        # Format and resize columns
        num_rows = len(records) + 1
        format_and_resize_columns(sheet, column_index, num_rows)


if __name__ == "__main__":
    import os

    try:
        # Load configuration from Config sheet
        from lib import env_constants
        from lib.config_loader import load_config_from_sheet

        default_reviewer_number, unexperienced_dev_names = load_config_from_sheet()
        env_constants.DEFAULT_REVIEWER_NUMBER = default_reviewer_number
        env_constants.UNEXPERIENCED_DEV_NAMES = unexperienced_dev_names

        teams = load_developers_from_sheet(
            EXPECTED_HEADERS_FOR_ROTATION,
            values_mapper=lambda record: Developer(
                name=record[TEAM_HEADER],
                reviewer_number=int(
                    record[TEAM_REVIEWER_NUMBER_HEADER] or DEFAULT_REVIEWER_NUMBER
                ),
                # Store team developers in preferable_reviewer_names field
                preferable_reviewer_names=parse_team_developers(
                    record[TEAM_DEVELOPERS_HEADER]
                ),
            ),
            sheet_index=TEAMS_SHEET,
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
        print(f"\n❌ Error during Teams rotation: {exc}")
        traceback.print_exc()
        raise  # Re-raise to ensure workflow fails
