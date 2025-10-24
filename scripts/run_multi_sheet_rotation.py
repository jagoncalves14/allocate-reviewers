"""
Multi-Sheet Rotation Runner

Runs developer and team rotations across multiple Google Sheets.
This script processes all sheets defined in SHEET_NAMES environment variable.

Usage:
    python scripts/run_multi_sheet_rotation.py --type devs
    python scripts/run_multi_sheet_rotation.py --type teams
    python scripts/run_multi_sheet_rotation.py --type all

Environment Variables:
    SHEET_NAMES: Multiline list of sheet names (one per line)
                 Example:
                 Front End - Code Reviewers
                 Backend - Code Reviewers
                 Mobile - Code Reviewers

    SHEET_NAME: Fallback to single sheet if SHEET_NAMES not set

Exit Codes:
    0: Success (all sheets processed)
    1: Partial failure (some sheets failed)
    2: Total failure (all sheets failed or no sheets configured)
"""
import os
import sys
import argparse
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# pylint: disable=wrong-import-position
from lib.env_constants import get_sheet_names  # noqa: E402


def run_devs_rotation_for_sheet(
    sheet_name: str, is_manual: bool = False
) -> bool:
    """
    Run individual developers rotation for a specific sheet.

    Args:
        sheet_name: Name of the Google Sheet to process
        is_manual: Whether this is a manual run

    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 80)
    print(f"📋 Processing Individual Developers Rotation: {sheet_name}")
    print("=" * 80 + "\n")

    try:
        # Import here to avoid conflicts
        from lib.config_loader import load_config_from_sheet
        from lib.utilities import (
            load_developers_from_sheet,
            update_current_sprint_reviewers,
        )
        from lib.env_constants import EXPECTED_HEADERS_FOR_ALLOCATION
        from scripts.rotate_devs_reviewers import (
            allocate_reviewers,
            write_reviewers_to_sheet,
        )
        from lib import env_constants

        # Load configuration from this sheet's Config tab
        default_reviewer_number, exp_dev_names = (
            load_config_from_sheet(sheet_name)
        )
        env_constants.DEFAULT_REVIEWER_NUMBER = default_reviewer_number
        env_constants.EXPERIENCED_DEV_NAMES = exp_dev_names

        # Load developers from this sheet
        developers = load_developers_from_sheet(
            EXPECTED_HEADERS_FOR_ALLOCATION,
            sheet_name=sheet_name,
        )

        # Allocate reviewers
        allocate_reviewers(developers)

        # Write results (manual vs scheduled)
        if is_manual:
            print("Manual run: Updating current sprint column")
            update_current_sprint_reviewers(
                EXPECTED_HEADERS_FOR_ALLOCATION,
                developers,
                sheet_name=sheet_name,
            )
        else:
            print("Scheduled run: Creating new sprint column")
            # Need to temporarily set SHEET_NAME for write_reviewers_to_sheet
            original_sheet_name = os.environ.get("SHEET_NAME")
            os.environ["SHEET_NAME"] = sheet_name
            try:
                write_reviewers_to_sheet(developers)
            finally:
                if original_sheet_name:
                    os.environ["SHEET_NAME"] = original_sheet_name
                else:
                    os.environ.pop("SHEET_NAME", None)

        print(f"✅ Successfully processed: {sheet_name}\n")
        return True

    except Exception as exc:  # noqa: BLE001 # pylint: disable=broad-except
        print(f"❌ Error processing {sheet_name}: {exc}")
        traceback.print_exc()
        return False


def run_teams_rotation_for_sheet(
    sheet_name: str, is_manual: bool = False
) -> bool:
    """
    Run teams rotation for a specific sheet.

    Args:
        sheet_name: Name of the Google Sheet to process
        is_manual: Whether this is a manual run

    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 80)
    print(f"👥 Processing Teams Rotation: {sheet_name}")
    print("=" * 80 + "\n")

    try:
        # Import here to avoid conflicts
        from lib.config_loader import load_config_from_sheet
        from lib.utilities import (
            load_developers_from_sheet,
            update_current_team_rotation,
        )
        from lib.env_constants import (
            EXPECTED_HEADERS_FOR_ROTATION,
            TEAM_HEADER,
            TEAM_DEVELOPERS_HEADER,
            TEAM_REVIEWER_NUMBER_HEADER,
        )
        from lib.data_types import Developer
        from scripts.rotate_team_reviewers import (
            assign_team_reviewers,
            write_reviewers_to_sheet as write_team_reviewers_to_sheet,
        )
        from lib import env_constants

        # Load configuration from this sheet's Config tab
        default_reviewer_number, exp_dev_names = (
            load_config_from_sheet(sheet_name)
        )
        env_constants.DEFAULT_REVIEWER_NUMBER = default_reviewer_number
        env_constants.EXPERIENCED_DEV_NAMES = exp_dev_names

        # Load teams from this sheet
        teams = load_developers_from_sheet(
            expected_headers=EXPECTED_HEADERS_FOR_ROTATION,
            values_mapper=lambda record: Developer(
                name=record[TEAM_HEADER],
                reviewer_number=int(
                    record[TEAM_REVIEWER_NUMBER_HEADER]
                    or default_reviewer_number
                ),
                preferable_reviewer_names=set(
                    name.strip()
                    for name in record[TEAM_DEVELOPERS_HEADER].split(",")
                    if name.strip()
                )
                if record[TEAM_DEVELOPERS_HEADER]
                else set(),
            ),
            sheet_index=2,  # Teams sheet
            sheet_name=sheet_name,
        )

        # Allocate reviewers
        assign_team_reviewers(teams)

        # Write results (manual vs scheduled)
        if is_manual:
            print("Manual run: Updating current rotation column")
            update_current_team_rotation(
                EXPECTED_HEADERS_FOR_ROTATION,
                teams,
                sheet_name=sheet_name,
            )
        else:
            print("Scheduled run: Creating new rotation column")
            # Temporarily set SHEET_NAME for write_team_reviewers_to_sheet
            original_sheet_name = os.environ.get("SHEET_NAME")
            os.environ["SHEET_NAME"] = sheet_name
            try:
                write_team_reviewers_to_sheet(teams)
            finally:
                if original_sheet_name:
                    os.environ["SHEET_NAME"] = original_sheet_name
                else:
                    os.environ.pop("SHEET_NAME", None)

        print(f"✅ Successfully processed: {sheet_name}\n")
        return True

    except Exception as exc:  # noqa: BLE001 # pylint: disable=broad-except
        print(f"❌ Error processing {sheet_name}: {exc}")
        traceback.print_exc()
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run rotations across multiple Google Sheets"
    )
    parser.add_argument(
        "--type",
        choices=["devs", "teams", "all"],
        default="all",
        help="Type of rotation to run (default: all)",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Run as manual execution (updates existing column)",
    )
    args = parser.parse_args()

    # Get list of sheets to process
    sheet_names = get_sheet_names()

    if not sheet_names:
        print("❌ Error: No sheets configured!")
        print("   Set SHEET_NAMES environment variable")
        print("   Format: One sheet name per line")
        sys.exit(2)

    print("\n🚀 Starting Multi-Sheet Rotation")
    print(f"   Type: {args.type}")
    print(f"   Mode: {'Manual' if args.manual else 'Scheduled'}")
    print(f"   Sheets to process: {len(sheet_names)}")
    for i, name in enumerate(sheet_names, 1):
        print(f"   {i}. {name}")
    print()

    # Track results
    results = {
        "total": len(sheet_names),
        "devs_success": 0,
        "devs_failed": 0,
        "teams_success": 0,
        "teams_failed": 0,
    }

    # Process each sheet
    for sheet_name in sheet_names:
        # Run developers rotation
        if args.type in ["devs", "all"]:
            if run_devs_rotation_for_sheet(sheet_name, args.manual):
                results["devs_success"] += 1
            else:
                results["devs_failed"] += 1

        # Run teams rotation
        if args.type in ["teams", "all"]:
            if run_teams_rotation_for_sheet(sheet_name, args.manual):
                results["teams_success"] += 1
            else:
                results["teams_failed"] += 1

    # Print summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total sheets: {results['total']}")

    if args.type in ["devs", "all"]:
        print("\nIndividual Developers Rotation:")
        print(f"  ✅ Success: {results['devs_success']}")
        print(f"  ❌ Failed:  {results['devs_failed']}")

    if args.type in ["teams", "all"]:
        print("\nTeams Rotation:")
        print(f"  ✅ Success: {results['teams_success']}")
        print(f"  ❌ Failed:  {results['teams_failed']}")

    # Determine exit code
    total_success = results["devs_success"] + results["teams_success"]
    total_failed = results["devs_failed"] + results["teams_failed"]

    if total_failed == 0:
        print("\n🎉 All rotations completed successfully!")
        sys.exit(0)
    elif total_success > 0:
        print("\n⚠️  Partial success - some sheets failed")
        sys.exit(1)
    else:
        print("\n❌ All rotations failed")
        sys.exit(2)


if __name__ == "__main__":
    main()
