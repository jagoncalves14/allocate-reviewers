import os
from dataclasses import asdict
from typing import Dict, List
from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time
from gspread import Spreadsheet, Worksheet
from oauth2client.service_account import ServiceAccountCredentials

from scripts.rotate_devs_reviewers import write_reviewers_to_sheet
from lib.utilities import (
    get_remote_sheet,
    load_developers_from_sheet,
)
from lib.data_types import Developer
from lib.env_constants import (
    DEVS_SHEET,
    DRIVE_SCOPE,
    EXPECTED_HEADERS_FOR_ALLOCATION,
    EXPECTED_HEADERS_FOR_ROTATION,
)
from tests.conftest import SHEET
from tests.utils import mutate_devs


@patch.dict(os.environ, {"CREDENTIAL_FILE": "credential_file.json", "SHEET_NAMES": "S"})
@patch("lib.utilities.ServiceAccountCredentials")
@patch("lib.utilities.gspread")
def test_get_remote_sheet(mocked_gspread: Mock, mocked_service_account: Mock) -> None:
    mocked_credential = Mock(spec=ServiceAccountCredentials)
    mocked_service_account.from_json_keyfile_name.return_value = (
        mocked_credential
    )

    mocked_client = Mock()
    mocked_gspread.authorize.return_value = mocked_client

    mocked_spreadsheet = Mock(spec=Spreadsheet)
    mocked_client.open.return_value = mocked_spreadsheet

    with get_remote_sheet(DEVS_SHEET) as _:
        mocked_service_account.from_json_keyfile_name.assert_called_once_with(
            "credential_file.json", DRIVE_SCOPE
        )
        mocked_gspread.authorize.assert_called_once_with(mocked_credential)

        mocked_client.open.assert_called_once_with("S")
        mocked_spreadsheet.get_worksheet.assert_called_once_with(DEVS_SHEET)

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
    devs = load_developers_from_sheet(headers)
    assert len(devs) == 5
    for idx, dev in enumerate(devs):
        assert asdict(dev) == asdict(mocked_devs[idx])


@freeze_time("2022-09-25 12:12:12")
def test_write_reviewers_to_sheet(
    mocked_devs: List[Developer],
) -> None:
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

