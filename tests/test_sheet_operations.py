import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time
from gspread import Spreadsheet, Worksheet
from oauth2client.service_account import ServiceAccountCredentials

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.data_types import Developer  # noqa: E402
from lib.env_constants import (  # noqa: E402
    DRIVE_SCOPE,
    EXPECTED_HEADERS_FOR_ALLOCATION,
    EXPECTED_HEADERS_FOR_ROTATION,
    SheetIndicesFallback,
)
from lib.utilities import (  # noqa: E402
    format_and_resize_columns,
    get_remote_sheet,
    load_developers_from_sheet,
    update_current_sprint_reviewers,
)
from scripts.rotate_devs_reviewers import write_reviewers_to_sheet  # noqa: E402
from tests.conftest import SHEET  # noqa: E402
from tests.utils import mutate_devs  # noqa: E402


@patch.dict(os.environ, {"CREDENTIAL_FILE": "credential_file.json", "SHEET_NAMES": "S"})
@patch("lib.utilities.ServiceAccountCredentials")
@patch("lib.utilities.gspread")
def test_get_remote_sheet(mocked_gspread: Mock, mocked_service_account: Mock) -> None:
    """Test that get_remote_sheet initializes and returns a worksheet."""
    mocked_credential = Mock(spec=ServiceAccountCredentials)
    mocked_service_account.from_json_keyfile_name.return_value = mocked_credential

    mocked_client = Mock()
    mocked_gspread.authorize.return_value = mocked_client

    mocked_spreadsheet = Mock(spec=Spreadsheet)
    mocked_client.open.return_value = mocked_spreadsheet

    with get_remote_sheet(SheetIndicesFallback.DEVS.value) as _:
        mocked_service_account.from_json_keyfile_name.assert_called_once_with(
            "credential_file.json", DRIVE_SCOPE
        )
        mocked_gspread.authorize.assert_called_once_with(mocked_credential)

        mocked_client.open.assert_called_once_with("S")
        mocked_spreadsheet.get_worksheet.assert_called_once_with(SheetIndicesFallback.DEVS.value)

        mocked_client.session.close.assert_not_called()

    mocked_client.session.close.assert_called_once()


@pytest.mark.parametrize(
    "headers", [EXPECTED_HEADERS_FOR_ALLOCATION, EXPECTED_HEADERS_FOR_ROTATION]
)
def test_load_developers_from_sheet(
    mocked_sheet_data: List[Dict[str, str]],
    mocked_devs: List[Developer],
    headers: List[str],
) -> None:
    """Test that load_developers_from_sheet correctly parses sheet data."""
    devs = load_developers_from_sheet(headers)
    assert len(devs) == 5
    for idx, dev in enumerate(devs):
        assert asdict(dev) == asdict(mocked_devs[idx])


@freeze_time("2022-09-25 12:12:12")
def test_write_reviewers_to_sheet(
    mocked_devs: List[Developer],
) -> None:
    """Test write_reviewers_to_sheet inserts a new column correctly."""
    with patch("scripts.rotate_devs_reviewers.get_remote_sheet") as mocked_get_remote_sheet:
        with mocked_get_remote_sheet() as mocked_sheet:
            DEV_REVIEWERS_MAPPER = {
                "B": set(("C", "D")),
                "E": set(("C", "A")),
            }
            mutate_devs(mocked_devs, "reviewer_names", DEV_REVIEWERS_MAPPER)
            new_column = [["25-09-2022", "", "C, D", "", "", "A, C"]]

            mocked_sheet.get_all_records.return_value = SHEET
            write_reviewers_to_sheet(mocked_devs)
            mocked_sheet.insert_cols.assert_called_once_with(new_column, 4)


def test_format_and_resize_columns_batch_update() -> None:
    """Test format_and_resize_columns batches all operations into one call."""
    mocked_sheet = Mock(spec=Worksheet)
    mocked_sheet.id = 123
    mocked_sheet.col_count = 5
    mocked_spreadsheet = Mock()
    mocked_sheet.spreadsheet = mocked_spreadsheet

    # Call with column 4, 6 rows (including header)
    format_and_resize_columns(mocked_sheet, column_index=4, num_rows=6)

    # Should make exactly ONE batch_update call
    assert mocked_spreadsheet.batch_update.call_count == 1

    # Get the requests from the call
    call_args = mocked_spreadsheet.batch_update.call_args[0][0]
    requests = call_args["requests"]

    # Should have 6 requests:
    # 1. repeatCell for current header
    # 2. repeatCell for current data
    # 3. repeatCell for old header
    # 4. repeatCell for old data
    # 5. updateDimensionProperties for current column (280px)
    # 6. updateDimensionProperties for old column (132px)
    assert len(requests) == 6

    # Verify current column header format (light blue, bold)
    assert requests[0]["repeatCell"]["cell"]["userEnteredFormat"]["backgroundColor"] == {
        "red": 0.85,
        "green": 0.92,
        "blue": 1,
    }
    assert requests[0]["repeatCell"]["cell"]["userEnteredFormat"]["textFormat"]["bold"] is True

    # Verify old column header format (grey, not bold)
    assert requests[2]["repeatCell"]["cell"]["userEnteredFormat"]["backgroundColor"] == {
        "red": 1,
        "green": 1,
        "blue": 1,
    }
    assert requests[2]["repeatCell"]["cell"]["userEnteredFormat"]["textFormat"]["bold"] is False
    old_foreground = requests[2]["repeatCell"]["cell"]["userEnteredFormat"]["textFormat"][
        "foregroundColor"
    ]
    assert old_foreground == {"red": 0.8, "green": 0.8, "blue": 0.8}

    # Verify current column resize (280px)
    resize_props = requests[4]["updateDimensionProperties"]["properties"]
    assert resize_props["pixelSize"] == 280
    assert requests[4]["updateDimensionProperties"]["range"]["startIndex"] == 3
    assert requests[4]["updateDimensionProperties"]["range"]["endIndex"] == 4

    # Verify old column resize (132px)
    old_resize_props = requests[5]["updateDimensionProperties"]["properties"]
    assert old_resize_props["pixelSize"] == 132
    assert requests[5]["updateDimensionProperties"]["range"]["startIndex"] == 4
    assert requests[5]["updateDimensionProperties"]["range"]["endIndex"] == 5


def test_format_and_resize_columns_no_old_columns() -> None:
    """Test formatting when there are no old columns to style."""
    mocked_sheet = Mock(spec=Worksheet)
    mocked_sheet.id = 123
    mocked_sheet.col_count = 4  # No columns after column 4
    mocked_spreadsheet = Mock()
    mocked_sheet.spreadsheet = mocked_spreadsheet

    format_and_resize_columns(mocked_sheet, column_index=4, num_rows=3)

    # Should still make ONE batch_update call
    assert mocked_spreadsheet.batch_update.call_count == 1

    # Get the requests from the call
    call_args = mocked_spreadsheet.batch_update.call_args[0][0]
    requests = call_args["requests"]

    # Should have only 3 requests (no old column operations):
    # 1. repeatCell for current header
    # 2. repeatCell for current data
    # 3. updateDimensionProperties for current column
    assert len(requests) == 3


@freeze_time("2022-10-15 10:30:00")
def test_update_current_sprint_reviewers_batch_update(
    mocked_devs: List[Developer],
) -> None:
    """
    Test update_current_sprint_reviewers uses batch update for all cells.

    Verifies NO individual update_cell() calls are made and that
    a single sheet.update() call is used instead for efficiency.
    """
    with patch("lib.utilities.get_remote_sheet") as mocked_get_remote_sheet:
        with mocked_get_remote_sheet() as mocked_sheet:
            # Setup
            mocked_sheet.row_values.return_value = [
                "Developer",
                "Number",
                "Preferable",
                "10-10-2022",
            ]
            mocked_sheet.get_all_records.return_value = SHEET
            mocked_sheet.id = 456
            mocked_sheet.col_count = 5
            mocked_spreadsheet = Mock()
            mocked_sheet.spreadsheet = mocked_spreadsheet

            DEV_REVIEWERS_MAPPER = {
                "B": set(("C", "D")),
                "E": set(("A",)),
            }
            mutate_devs(mocked_devs, "reviewer_names", DEV_REVIEWERS_MAPPER)

            # Call the function
            update_current_sprint_reviewers(EXPECTED_HEADERS_FOR_ALLOCATION, mocked_devs)

            # Should NOT call update_cell at all
            assert not mocked_sheet.update_cell.called

            # Should call sheet.update() exactly once for data
            assert mocked_sheet.update.call_count == 1

            # Verify the update call
            update_call_args = mocked_sheet.update.call_args[0]
            range_str = update_call_args[0]
            data = update_call_args[1]

            # Range should be D1:D6 (column 4, 6 rows)
            assert range_str == "D1:D6"

            # Data should be [[header], [row1], [row2], [row3], [row4], [row5]]
            assert len(data) == 6
            assert data[0][0] == "10-10-2022 / Manual Run on: 15-10-2022"
            assert data[2][0] == "C, D"  # Developer B
            assert data[5][0] == "A"  # Developer E
