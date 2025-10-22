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


def column_number_to_letter(col_num: int) -> str:
    """Convert column number to Excel-style letter (1=A, 27=AA, etc.)"""
    result = ""
    while col_num > 0:
        col_num -= 1
        result = chr(65 + (col_num % 26)) + result
        col_num //= 26
    return result


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
        
        # Style older columns to the right: light grey text, normal weight
        num_rows = len(records) + 1
        last_col = sheet.col_count
        if last_col > column_index:
            for col in range(column_index + 1, last_col + 1):
                col_letter = column_number_to_letter(col)
                # Header: white background, light grey text
                sheet.format(f"{col_letter}1", {
                    "backgroundColor": {"red": 1, "green": 1, "blue": 1},
                    "textFormat": {
                        "foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6},
                        "fontWeight": 400
                    }
                })
                # Data rows: light grey text, normal weight
                if num_rows > 1:
                    sheet.format(f"{col_letter}2:{col_letter}{num_rows}", {
                        "textFormat": {
                            "foregroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6},
                            "fontWeight": 400
                        }
                    })
        
        # Apply light blue background ONLY to header of current column
        col_letter = column_number_to_letter(column_index)
        sheet.format(f"{col_letter}1", {
            "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 1},
            "textFormat": {
                "foregroundColor": {"red": 0, "green": 0, "blue": 0},
                "fontWeight": 700
            }
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
