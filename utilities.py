import os
from contextlib import contextmanager
from typing import List, Callable

import gspread
from dotenv import find_dotenv, load_dotenv
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

from data_types import Developer
from env_constants import (
    DRIVE_SCOPE,
    DEVELOPER_HEADER,
    REVIEWER_NUMBER_HEADER,
    DEFAULT_REVIEWER_NUMBER,
    PREFERABLE_REVIEWER_HEADER,
)

load_dotenv(find_dotenv())


def load_developers_from_sheet(
    expected_headers: List[str],
    values_mapper: Callable[[dict], Developer] = lambda record: Developer(
        name=record[DEVELOPER_HEADER],
        reviewer_number=int(
            record[REVIEWER_NUMBER_HEADER] or DEFAULT_REVIEWER_NUMBER
        ),
        preferable_reviewer_names=set(
            (record[PREFERABLE_REVIEWER_HEADER]).split(", ")
        )
        if record[PREFERABLE_REVIEWER_HEADER]
        else set(),
    ),
) -> List[Developer]:
    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(expected_headers=expected_headers)

    input_developers = map(
        values_mapper,
        records,
    )

    return list(input_developers)


@contextmanager
def get_remote_sheet() -> Worksheet:
    CREDENTIAL_FILE = os.environ.get("CREDENTIAL_FILE")
    SHEET_NAME = os.environ.get("SHEET_NAME")

    credential = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIAL_FILE, DRIVE_SCOPE
    )
    client = gspread.authorize(credential)
    sheet = client.open(SHEET_NAME).sheet1
    yield sheet
    client.session.close()


def write_exception_to_sheet(
    expected_headers: List[str],
    error: str,
) -> None:
    column_index = len(expected_headers) + 1
    new_column = [f"Exception {datetime.now().strftime('%d-%m-%Y')}", error]

    with get_remote_sheet() as sheet:
        sheet.insert_cols([new_column], column_index)


def update_current_sprint_reviewers(
    expected_headers: List[str], devs: List[Developer]
) -> None:
    """Update reviewers in the current sprint column (for manual runs)"""
    column_index = len(expected_headers) + 1

    with get_remote_sheet() as sheet:
        # Get the current header
        first_row = sheet.row_values(1)
        current_header = (
            first_row[column_index - 1]
            if len(first_row) >= column_index
            else None
        )

        if not current_header:
            # No existing sprint column, create one
            print("No existing sprint found, creating new column")
            from allocate_reviewers import write_reviewers_to_sheet

            write_reviewers_to_sheet(devs)
            return

        # Extract original sprint date from header
        if " / Manual Run on:" in current_header:
            # Already has manual run info, extract sprint date
            sprint_date = current_header.split(" / Manual Run on:")[0].strip()
        else:
            # First manual run on this sprint
            sprint_date = current_header

        # Create new header with manual run info
        today = datetime.now().strftime("%d-%m-%Y")
        new_header = f"{sprint_date} / Manual Run on: {today}"

        # Update the column
        records = sheet.get_all_records(expected_headers=expected_headers)

        # Update header
        sheet.update_cell(1, column_index, new_header)

        # Update reviewer assignments
        for idx, record in enumerate(records, start=2):
            developer = next(
                dev for dev in devs if dev.name == record[DEVELOPER_HEADER]
            )
            reviewer_names = ", ".join(sorted(developer.reviewer_names))
            sheet.update_cell(idx, column_index, reviewer_names)
        
        # Clear background color from all date columns (D onwards)
        last_col = sheet.col_count
        if last_col >= column_index:
            range_to_clear = f"{chr(64 + column_index + 1)}1:{chr(64 + last_col)}{len(records) + 1}"
            sheet.format(range_to_clear, {"backgroundColor": {"red": 1, "green": 1, "blue": 1}})
        
        # Apply background color to the current column (most recent)
        num_rows = len(records) + 1
        col_letter = chr(64 + column_index)
        range_to_color = f"{col_letter}1:{col_letter}{num_rows}"
        sheet.format(range_to_color, {
            "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 1}  # Light blue
        })
        
        # Set column width to 280px for manual runs
        body = {
            "requests": [
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet.id,
                            "dimension": "COLUMNS",
                            "startIndex": column_index - 1,
                            "endIndex": column_index
                        },
                        "properties": {
                            "pixelSize": 280
                        },
                        "fields": "pixelSize"
                    }
                }
            ]
        }
        sheet.spreadsheet.batch_update(body)
