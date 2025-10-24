"""Test fixtures for pytest."""

from copy import deepcopy
from typing import Dict, Generator, List
from unittest.mock import patch

import pytest
from gspread import Worksheet

from lib.data_types import Developer

SHEET = [
    {
        "Developer": "A",
        "Number of Reviewers": "",
        "Preferable Reviewers": "B, C",
    },
    {
        "Developer": "B",
        "Number of Reviewers": "2",
        "Preferable Reviewers": "",
    },
    {
        "Developer": "C",
        "Number of Reviewers": "3",
        "Preferable Reviewers": "",
    },
    {
        "Developer": "D",
        "Number of Reviewers": "3",
        "Preferable Reviewers": "",
    },
    {
        "Developer": "E",
        "Number of Reviewers": "5",
        "Preferable Reviewers": "",
    },
]

DEVS = [
    Developer(
        name="A", reviewer_number=1, preferable_reviewer_names=set(("B", "C"))
    ),
    Developer(name="B", reviewer_number=2, preferable_reviewer_names=set()),
    Developer(name="C", reviewer_number=3, preferable_reviewer_names=set()),
    Developer(name="D", reviewer_number=3, preferable_reviewer_names=set()),
    Developer(name="E", reviewer_number=5, preferable_reviewer_names=set()),
]


@pytest.fixture(scope="function")
def mocked_sheet() -> Generator[Worksheet, None, None]:
    """Provide a mocked worksheet for testing."""
    with patch("lib.utilities.get_remote_sheet") as mocked_get_remote_sheet:
        with mocked_get_remote_sheet() as mocked_sheet:
            yield mocked_sheet


@pytest.fixture(scope="function")
def mocked_sheet_data(
    mocked_sheet: Worksheet,
) -> Generator[List[Dict[str, str]], None, None]:
    """Provide mocked sheet data for testing."""
    mocked_sheet.get_all_records.return_value = SHEET
    yield SHEET


@pytest.fixture(scope="function")
def mocked_devs() -> Generator[List[Developer], None, None]:
    """Provide a fresh copy of developer test data."""
    devs = deepcopy(DEVS)
    yield devs
