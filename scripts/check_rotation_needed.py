"""
Check if a rotation is needed based on the last execution date
in the Google Sheet.
Exit code 0: Rotation needed (14+ days since last rotation)
Exit code 1: Rotation not needed yet
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# pylint: next-line: disable=wrong-import-position
from lib.env_constants import (  # noqa: E402
    EXPECTED_HEADERS_FOR_ALLOCATION,
    EXPECTED_HEADERS_FOR_ROTATION,
    MINIMUM_DAYS_BETWEEN_ROTATIONS,
    ROTATION_TYPES,
)

DRIVE_SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]


def get_last_rotation_date(expected_headers: list[str], sheet_index: int = 0) -> datetime | None:
    """
    Read the Google Sheet and find the most recent rotation date.
    The date is stored in the header row after the first 3 columns.
    Format: dd-mm-yyyy or "dd-mm-yyyy / Manual Run on: dd-mm-yyyy"
    For manual runs, we extract the Sprint Date (before the " / ")
    to maintain schedule.
    """
    credential_file = os.environ.get("CREDENTIAL_FILE")
    sheet_name = os.environ.get("SHEET_NAME")

    if not credential_file or not sheet_name:
        print("Error: CREDENTIAL_FILE and SHEET_NAME environment variables are required")
        sys.exit(1)

    try:
        credential = ServiceAccountCredentials.from_json_keyfile_name(credential_file, DRIVE_SCOPE)
        client = gspread.authorize(credential)
        spreadsheet = client.open(sheet_name)
        sheet = spreadsheet.get_worksheet(sheet_index)

        # Get the first row (headers)
        first_row = sheet.row_values(1)

        # Skip the first N columns (before date columns)
        date_columns = first_row[len(expected_headers) :]  # noqa: E203

        if not date_columns:
            print("No previous rotations found in the sheet")
            return None

        # Get the most recent date (first column after the headers)
        last_date_str = date_columns[0]

        # Check if it's a manual run header
        if " / Manual Run on:" in last_date_str:
            # Extract the sprint date (before " / Manual Run on:")
            sprint_date_str = last_date_str.split(" / Manual Run on:")[0].strip()
            try:
                last_date = datetime.strptime(sprint_date_str, "%d-%m-%Y")
                print(f"Last sprint date (from manual run): " f"{last_date.strftime('%d-%m-%Y')}")
                return last_date
            except ValueError:
                print(f"Warning: Could not parse sprint date " f"'{sprint_date_str}'")
                return None
        else:
            # Regular scheduled run
            try:
                last_date = datetime.strptime(last_date_str, "%d-%m-%Y")
                print(f"Last rotation date: " f"{last_date.strftime('%d-%m-%Y')}")
                return last_date
            except ValueError:
                print(
                    f"Warning: Could not parse date '{last_date_str}' - "
                    f"assuming no valid previous rotation"
                )
                return None

    except Exception as exc:  # noqa: BLE001
        print(f"Error reading sheet: {exc}")
        sys.exit(1)


def main() -> None:
    """
    Main entry point to check if rotation is needed based on date threshold.

    Reads the last rotation date from the Google Sheet and exits with:
    - Exit code 0: Rotation is needed (14+ days passed)
    - Exit code 1: Rotation not needed or error occurred
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Check if rotation is needed (14+ days)")
    parser.add_argument(
        "--sheet-type",
        choices=ROTATION_TYPES,
        default="devs",
        help="Type of sheet to check (default: devs)",
    )
    args = parser.parse_args()

    # Auto-detect sheet indices
    from lib.env_constants import SheetIndicesFallback, SheetTypes
    from scripts.run_multi_sheet_rotation import detect_all_sheet_types

    sheet_name = os.environ.get("SHEET_NAME")
    if not sheet_name:
        print("Error: SHEET_NAME environment variable is required")
        sys.exit(1)

    print(f"🔍 Auto-detecting sheet types in: {sheet_name}")
    detected_sheets = detect_all_sheet_types(sheet_name)

    # Select appropriate headers and sheet index based on sheet type
    if args.sheet_type == "teams":
        expected_headers = EXPECTED_HEADERS_FOR_ROTATION
        # Use detected index or fall back to constant
        sheet_index = detected_sheets.get(SheetTypes.TEAMS, SheetIndicesFallback.TEAMS.value)
        if SheetTypes.TEAMS in detected_sheets:
            print(f"✅ Using detected Teams sheet at index {sheet_index}")
        else:
            print(
                f"⚠️  Teams sheet not detected, using default index "
                f"{SheetIndicesFallback.TEAMS.value}"
            )
            sheet_index = SheetIndicesFallback.TEAMS.value
    else:
        expected_headers = EXPECTED_HEADERS_FOR_ALLOCATION
        # Use detected index or fall back to constant
        sheet_index = detected_sheets.get(SheetTypes.DEVS, SheetIndicesFallback.DEVS.value)
        if SheetTypes.DEVS in detected_sheets:
            print(f"✅ Using detected Devs sheet at index {sheet_index}")
        else:
            print(
                f"⚠️  Devs sheet not detected, using default index "
                f"{SheetIndicesFallback.DEVS.value}"
            )
            sheet_index = SheetIndicesFallback.DEVS.value

    last_rotation_date = get_last_rotation_date(expected_headers, sheet_index)

    if last_rotation_date is None:
        print("No previous rotation found - rotation is needed")
        sys.exit(0)

    today = datetime.now()
    days_since_last_rotation = (today - last_rotation_date).days

    print(f"Days since last rotation: {days_since_last_rotation}")

    if days_since_last_rotation >= MINIMUM_DAYS_BETWEEN_ROTATIONS:
        print(
            f"Rotation needed ({days_since_last_rotation} >= "
            f"{MINIMUM_DAYS_BETWEEN_ROTATIONS} days)"
        )
        sys.exit(0)
    else:
        print(
            f"Rotation not needed yet ({days_since_last_rotation} < "
            f"{MINIMUM_DAYS_BETWEEN_ROTATIONS} days)"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
