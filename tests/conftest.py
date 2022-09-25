from unittest.mock import patch

import pytest

SHEET = [
    {
        "Developer": "A",
        "Reviewer Number": "",
        "Preferable Reviewers": "B, C",
    },
    {
        "Developer": "B",
        "Reviewer Number": "2",
        "Preferable Reviewers": "",
    },
    {
        "Developer": "C",
        "Reviewer Number": "3",
        "Preferable Reviewers": "",
    },
    {
        "Developer": "D",
        "Reviewer Number": "3",
        "Preferable Reviewers": "",
    },
    {
        "Developer": "E",
        "Reviewer Number": "5",
        "Preferable Reviewers": "",
    },
]


@pytest.fixture(scope="function")
def mocked_sheet():
    with patch("allocate_reviewers.get_remote_sheet") as mocked_get_remote_sheet:
        with mocked_get_remote_sheet() as mocked_sheet:
            yield mocked_sheet


@pytest.fixture(scope="function")
def mocked_sheet_data(mocked_sheet):
    mocked_sheet.get_all_records.return_value = SHEET
    yield SHEET
