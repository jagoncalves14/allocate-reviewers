import os
from contextlib import contextmanager
from typing import List, Callable
from datetime import datetime

import gspread
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import find_dotenv, load_dotenv

from lib.data_types import Developer
from lib.env_constants import (
    DRIVE_SCOPE,
    DEVELOPER_HEADER,
    REVIEWER_NUMBER_HEADER,
    DEFAULT_REVIEWER_NUMBER,
    PREFERABLE_REVIEWER_HEADER,
    DEVS_SHEET,
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


def format_column(
    sheet: Worksheet,
    column_index: int,
    num_rows: int,
    background_color: dict,
    text_color: dict,
    bold: bool = False,
) -> None:
    """
    Generic function to format a single column with custom styling.

    Note: This function only applies color/text formatting.
    Use format_and_resize_columns() to also resize columns efficiently.

    Args:
        sheet: The worksheet to format
        column_index: The index of the column to format (1-based)
        num_rows: Total number of rows (including header)
        background_color: RGB dict like {"red": 1, "green": 1, "blue": 1}
        text_color: RGB dict like {"red": 0, "green": 0, "blue": 0}
        bold: Whether text should be bold (default: False)
    """
    col_letter = column_number_to_letter(column_index)

    # Format header (row 1)
    sheet.format(
        f"{col_letter}1",
        {
            "backgroundColor": background_color,
            "textFormat": {
                "foregroundColor": text_color,
                "bold": bold,
            },
        },
    )

    # Format data rows (row 2 onwards)
    if num_rows > 1:
        sheet.format(
            f"{col_letter}2:{col_letter}{num_rows}",
            {
                "backgroundColor": background_color,
                "textFormat": {
                    "foregroundColor": text_color,
                    "bold": bold,
                }
            },
        )


def format_current_date_column(
    sheet: Worksheet,
    column_index: int,
    num_rows: int,
) -> None:
    """
    Format the current date column with light blue background.

    Note: Does not resize. Use format_and_resize_columns() for resizing.

    Args:
        sheet: The worksheet to format
        column_index: The index of the column to format (1-based)
        num_rows: Total number of rows (including header)
    """
    format_column(
        sheet=sheet,
        column_index=column_index,
        num_rows=num_rows,
        background_color={"red": 0.85, "green": 0.92, "blue": 1},
        text_color={"red": 0, "green": 0, "blue": 0},
        bold=True,
    )


def format_old_date_column(
    sheet: Worksheet,
    column_index: int,
    num_rows: int,
) -> None:
    """
    Format an old date column with grey styling.

    Note: Does not resize. Use format_and_resize_columns() for resizing.

    Args:
        sheet: The worksheet to format
        column_index: The index of the column to format (1-based)
        num_rows: Total number of rows (including header)
    """
    format_column(
        sheet=sheet,
        column_index=column_index,
        num_rows=num_rows,
        background_color={"red": 1, "green": 1, "blue": 1},
        text_color={"red": 0.8, "green": 0.8, "blue": 0.8},
        bold=False,
    )


def format_and_resize_columns(
    sheet: Worksheet,
    column_index: int,
    num_rows: int,
    num_old_columns_to_style: int = 1,
) -> None:
    """
    Apply formatting and resizing to current and older columns.

    Args:
        sheet: The worksheet to format
        column_index: The index of the current/new column (1-based)
        num_rows: Total number of rows (including header)
        num_old_columns_to_style: Number of older columns to style (default: 1)

    Formatting applied:
    - Current column: light blue header, bold, 280px width
    - Older columns: grey header/data, not bold, 132px width

    All resize operations are batched into a single API call for efficiency.
    """
    last_col = sheet.col_count

    try:
        # Format current date column (color/text only)
        format_current_date_column(sheet, column_index, num_rows)

        # Format older columns (if they exist, color/text only)
        if last_col > column_index:
            max_cols = min(num_old_columns_to_style, last_col - column_index)
            for i in range(1, max_cols + 1):
                col = column_index + i
                format_old_date_column(sheet, col, num_rows)

        # Batch all resize operations into a single API call
        resize_requests = [
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet.id,
                        "dimension": "COLUMNS",
                        "startIndex": column_index - 1,
                        "endIndex": column_index,
                    },
                    "properties": {"pixelSize": 280},
                    "fields": "pixelSize",
                }
            }
        ]

        # Add old columns resize (if they exist)
        if last_col > column_index:
            max_cols = min(num_old_columns_to_style, last_col - column_index)
            if max_cols > 0:
                resize_requests.append({
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet.id,
                            "dimension": "COLUMNS",
                            "startIndex": column_index,
                            "endIndex": column_index + max_cols,
                        },
                        "properties": {"pixelSize": 132},
                        "fields": "pixelSize",
                    }
                })

        # Single batch_update call for all resizes
        sheet.spreadsheet.batch_update({"requests": resize_requests})

    except Exception as e:  # noqa: BLE001
        print(f"Note: Column formatting/resizing skipped: {e}")


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
    sheet_index: int = DEVS_SHEET,
    sheet_name: str | None = None,
) -> List[Developer]:
    with get_remote_sheet(sheet_index, sheet_name) as sheet:
        records = sheet.get_all_records(expected_headers=expected_headers)

    input_developers = map(
        values_mapper,
        records,
    )

    return list(input_developers)


@contextmanager
def get_remote_sheet(
    sheet_index: int = DEVS_SHEET, sheet_name: str | None = None
) -> Worksheet:
    """
    Fetch the Worksheet data from remote Google sheet

    Args:
        sheet_index: Index of the sheet tab
            (0=Config, 1=Individual Developers, 2=Teams)
        sheet_name: Name of the Google Sheet file to open.
            If None, uses first sheet from SHEET_NAMES environment variable.
            For multi-sheet support, pass the specific sheet name.
    """
    CREDENTIAL_FILE = os.environ.get("CREDENTIAL_FILE")

    # Use provided sheet_name or fall back to first sheet in SHEET_NAMES
    if sheet_name is None:
        from lib.env_constants import get_sheet_names
        sheets = get_sheet_names()
        if sheets:
            sheet_name = sheets[0]

    if not sheet_name:
        raise ValueError(
            "Sheet name must be provided either as parameter or "
            "via SHEET_NAMES environment variable"
        )

    credential = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIAL_FILE, DRIVE_SCOPE
    )
    client = gspread.authorize(credential)
    spreadsheet = client.open(sheet_name)
    # Get sheet by index (0-based)
    sheet = spreadsheet.get_worksheet(sheet_index)
    yield sheet
    client.session.close()


def update_current_sprint_reviewers(
    expected_headers: List[str],
    devs: List[Developer],
    sheet_index: int = DEVS_SHEET,
    sheet_name: str | None = None,
) -> None:
    """Update reviewers in the current sprint column (for manual runs)"""
    column_index = len(expected_headers) + 1

    with get_remote_sheet(sheet_index, sheet_name) as sheet:
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

        # Format and resize columns
        num_rows = len(records) + 1
        format_and_resize_columns(sheet, column_index, num_rows)


def update_current_team_rotation(
    expected_headers: List[str],
    teams: List[Developer],
    sheet_name: str | None = None,
) -> None:
    """
    Update reviewers in the current rotation column (manual runs, 2nd sheet)
    """
    from lib.env_constants import TEAM_HEADER

    column_index = len(expected_headers) + 1

    from lib.env_constants import TEAMS_SHEET

    with get_remote_sheet(TEAMS_SHEET, sheet_name) as sheet:
        # Get the current header
        first_row = sheet.row_values(1)
        current_header = (
            first_row[column_index - 1]
            if len(first_row) >= column_index
            else None
        )

        if not current_header or current_header.startswith("Exception"):
            # No existing rotation column or exception, create new one
            print("No valid rotation found, creating new column")
            from rotate_reviewers import write_reviewers_to_sheet

            write_reviewers_to_sheet(teams)
            return

        # Extract original rotation date from header
        if " / Manual Run on:" in current_header:
            # Already has manual run info, extract rotation date
            rotation_date = (
                current_header.split(" / Manual Run on:")[0].strip()
            )
        else:
            # First manual run on this rotation
            rotation_date = current_header

        # Create new header with manual run info
        today = datetime.now().strftime("%d-%m-%Y")
        new_header = f"{rotation_date} / Manual Run on: {today}"

        # Update the columns
        records = sheet.get_all_records(expected_headers=expected_headers)

        # Update reviewers column header
        sheet.update_cell(1, column_index, new_header)

        # Update reviewer assignments
        for idx, record in enumerate(records, start=2):
            team = next(t for t in teams if t.name == record[TEAM_HEADER])
            reviewer_names = ", ".join(sorted(team.reviewer_names))
            sheet.update_cell(idx, column_index, reviewer_names)

        # Format and resize columns
        num_rows = len(records) + 1
        format_and_resize_columns(sheet, column_index, num_rows)
