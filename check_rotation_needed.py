"""
Check if a rotation is needed based on the last execution date
in the Google Sheet.
Exit code 0: Rotation needed (15+ days since last rotation)
Exit code 1: Rotation not needed yet
"""
import os
import sys
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

DRIVE_SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

MINIMUM_DAYS_BETWEEN_ROTATIONS = 15


def get_last_rotation_date() -> datetime | None:
    """
    Read the Google Sheet and find the most recent rotation date.
    The date is stored in the header row after the first 3 columns.
    Format: dd-mm-yyyy or "dd-mm-yyyy / Manual Run on: dd-mm-yyyy"
    For manual runs, we extract the Sprint Date (before the " / ")
    to maintain schedule.
    """
    CREDENTIAL_FILE = os.environ.get("CREDENTIAL_FILE")
    SHEET_NAME = os.environ.get("SHEET_NAME")

    if not CREDENTIAL_FILE or not SHEET_NAME:
        print(
            "Error: CREDENTIAL_FILE and SHEET_NAME environment "
            "variables are required"
        )
        sys.exit(1)

    try:
        credential = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIAL_FILE, DRIVE_SCOPE
        )
        client = gspread.authorize(credential)
        sheet = client.open(SHEET_NAME).sheet1

        # Get the first row (headers)
        first_row = sheet.row_values(1)

        # The first 3 columns are: Developer, Reviewer Number,
        # Preferable Reviewers. After that, we have date columns
        date_columns = first_row[3:]  # Skip the first 3 headers

        if not date_columns:
            print("No previous rotations found in the sheet")
            return None

        # Get the most recent date (first column after the headers)
        last_date_str = date_columns[0]

        # Check if it's a manual run header
        if " / Manual Run on:" in last_date_str:
            # Extract the sprint date (before the " / Manual Run on:")
            sprint_date_str = last_date_str.split(" / Manual Run on:")[0].strip()
            try:
                last_date = datetime.strptime(sprint_date_str, "%d-%m-%Y")
                print(
                    f"Last sprint date (from manual run): "
                    f"{last_date.strftime('%d-%m-%Y')}"
                )
                return last_date
            except ValueError:
                print(
                    f"Warning: Could not parse sprint date "
                    f"'{sprint_date_str}'"
                )
                return None
        else:
            # Regular scheduled run
            try:
                last_date = datetime.strptime(last_date_str, "%d-%m-%Y")
                print(
                    f"Last rotation date: "
                    f"{last_date.strftime('%d-%m-%Y')}"
                )
                return last_date
            except ValueError:
                print(
                    f"Warning: Could not parse date '{last_date_str}' - "
                    f"assuming no valid previous rotation"
                )
                return None

    except Exception as exc:
        print(f"Error reading sheet: {exc}")
        sys.exit(1)


def main() -> None:
    last_rotation_date = get_last_rotation_date()

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
