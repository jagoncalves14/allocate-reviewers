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
        reviewer_number=int(record[REVIEWER_NUMBER_HEADER] or DEFAULT_REVIEWER_NUMBER),
        preferable_reviewer_names=set((record[PREFERABLE_REVIEWER_HEADER]).split(", "))
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


def write_reviewers_to_sheet(
    expected_headers: List[str], devs: List[Developer]
) -> None:
    column_index = len(expected_headers) + 1
    column_header = datetime.now().strftime("%d-%m-%Y")
    new_column = [column_header]

    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(expected_headers=expected_headers)
        for record in records:
            developer = next(dev for dev in devs if dev.name == record["Developer"])
            reviewer_names = ", ".join(sorted(developer.reviewer_names))
            new_column.append(reviewer_names)
        sheet.insert_cols([new_column], column_index)
