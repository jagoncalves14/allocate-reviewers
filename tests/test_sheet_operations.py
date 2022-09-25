from copy import deepcopy
from dataclasses import asdict

from freezegun import freeze_time

from allocate_reviewers import (Developer, load_developers_from_sheet,
                                write_exception_to_sheet,
                                write_reviewers_to_sheet)
from tests.conftest import SHEET

EXPECTED_DEVS = [
    Developer(name="A", reviewer_number=1, preferable_reviewer_names=set(["B", "C"])),
    Developer(name="B", reviewer_number=2, preferable_reviewer_names=set()),
    Developer(name="C", reviewer_number=3, preferable_reviewer_names=set()),
    Developer(name="D", reviewer_number=3, preferable_reviewer_names=set()),
    Developer(name="E", reviewer_number=5, preferable_reviewer_names=set()),
]


def test_load_developers_from_sheet(mocked_sheet_data) -> None:

    devs = load_developers_from_sheet()
    assert len(devs) == 5
    for idx, dev in enumerate(devs):
        assert asdict(dev) == asdict(EXPECTED_DEVS[idx])


@freeze_time("2022-09-25 12:12:12")
def test_write_reviewers_to_sheet(mocked_sheet) -> None:
    devs = deepcopy(EXPECTED_DEVS)
    devs[1].reviewer_names = set(["C", "D"])
    devs[4].reviewer_names = set(["C", "A"])
    new_column = [["25-09-2022", "", "C, D", "", "", "A, C"]]

    mocked_sheet.get_all_records.return_value = SHEET
    write_reviewers_to_sheet(devs)

    mocked_sheet.insert_cols.assert_called_once_with(new_column, 4)


@freeze_time("2022-09-30 12:12:12")
def test_write_exception_to_sheet(mocked_sheet) -> None:
    new_column = [["Exception 30-09-2022", "Awesome error!"]]

    write_exception_to_sheet("Awesome error!")

    mocked_sheet.insert_cols.assert_called_once_with(new_column, 4)
