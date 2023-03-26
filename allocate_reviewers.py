import os
import random
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Set

import gspread
from dotenv import find_dotenv, load_dotenv
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv(find_dotenv())

DEFAULT_REVIEWER_NUMBER = int(os.environ.get("DEFAULT_REVIEWER_NUMBER") or "1")
EXPERIENCED_DEV_NAMES = set(os.environ.get("EXPERIENCED_DEV_NAMES", "").split(", "))

DRIVE_SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]
EXPECTED_HEADERS = ["Developer", "Reviewer Number", "Preferable Reviewers"]


@dataclass
class Developer:
    name: str
    reviewer_number: int
    preferable_reviewer_names: Set[str]
    reviewer_names: Set[str] = field(default_factory=set)
    review_for: Set[str] = field(default_factory=set)


@dataclass
class SelectableConfigure:
    names: Set[str]
    number_getter: Callable[[], int]


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


def load_developers_from_sheet() -> List[Developer]:
    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(expected_headers=EXPECTED_HEADERS)

    input_developers = map(
        lambda record: Developer(
            name=record["Developer"],
            reviewer_number=int(record["Reviewer Number"] or DEFAULT_REVIEWER_NUMBER),
            preferable_reviewer_names=set((record["Preferable Reviewers"]).split(", "))
            if record["Preferable Reviewers"]
            else set(),
        ),
        records,
    )

    return list(input_developers)


def shuffle_and_get_the_most_available_names(
    available_names: Set[str], number_of_names: int, devs
) -> List[str]:
    if number_of_names == 0:
        return []
    names = list(available_names)

    if 0 == len(names) <= number_of_names:
        return names

    random.shuffle(names)
    # To select names that have the least assigned times.
    names.sort(
        key=lambda name: len(next(dev for dev in devs if dev.name == name).review_for),
    )

    return names[0:number_of_names]


def allocate_reviewers(devs: List[Developer]) -> None:
    """
    Assign reviewers to input developers.
    The function mutate directly the input argument "devs".
    """
    EXPERIENCED_DEV_NAMES = set(os.environ.get("EXPERIENCED_DEV_NAMES", "").split(", "))

    all_dev_names = set((dev.name for dev in devs))
    valid_experienced_dev_names = set(
        (name for name in EXPERIENCED_DEV_NAMES if name in all_dev_names)
    )

    # To process devs with preferable_reviewer_names first.
    devs.sort(key=lambda dev: dev.preferable_reviewer_names, reverse=True)

    for developer in devs:
        chosen_reviewer_names: Set[str] = set()
        reviewer_number = min(developer.reviewer_number, len(all_dev_names) - 1)

        def selectable_number_getter() -> int:
            return max(reviewer_number - len(chosen_reviewer_names), 0)

        def experienced_reviewer_number_getter() -> int:
            experienced_reviewer_chosen = next(
                (
                    name
                    for name in chosen_reviewer_names
                    if name in valid_experienced_dev_names
                ),
                None,
            )
            if experienced_reviewer_chosen:
                return 0
            return max(min(1, reviewer_number - len(chosen_reviewer_names)), 0)

        configures = [
            SelectableConfigure(
                names=developer.preferable_reviewer_names,
                number_getter=selectable_number_getter,
            ),
            SelectableConfigure(
                names=valid_experienced_dev_names,
                number_getter=experienced_reviewer_number_getter,
            ),
            SelectableConfigure(
                names=set(
                    (
                        name
                        for name in all_dev_names
                        if name not in valid_experienced_dev_names
                    )
                ),
                number_getter=selectable_number_getter,
            ),
            SelectableConfigure(
                names=all_dev_names,
                number_getter=selectable_number_getter,
            ),
        ]

        for configure in configures:
            selectable_names = set(
                (
                    name
                    for name in configure.names
                    if name not in [developer.name, *chosen_reviewer_names]
                )
            )
            selectable_number = configure.number_getter()
            chosen_names = shuffle_and_get_the_most_available_names(
                selectable_names, selectable_number, devs
            )
            chosen_reviewer_names.update(chosen_names)

        reviewers = (dev for dev in devs if dev.name in chosen_reviewer_names)
        for reviewer in reviewers:
            developer.reviewer_names.add(reviewer.name)
            reviewer.review_for.add(developer.name)


def write_reviewers_to_sheet(devs: List[Developer]) -> None:
    column_index = len(EXPECTED_HEADERS) + 1
    column_header = datetime.now().strftime("%d-%m-%Y")
    new_column = [column_header]

    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(expected_headers=EXPECTED_HEADERS)
        for record in records:
            developer = next(dev for dev in devs if dev.name == record["Developer"])
            reviewer_names = ", ".join(sorted(developer.reviewer_names))
            new_column.append(reviewer_names)
        sheet.insert_cols([new_column], column_index)


def write_exception_to_sheet(error: str) -> None:
    column_index = len(EXPECTED_HEADERS) + 1
    new_column = [f"Exception {datetime.now().strftime('%d-%m-%Y')}", error]

    with get_remote_sheet() as sheet:
        sheet.insert_cols([new_column], column_index)


if __name__ == "__main__":
    try:
        developers = load_developers_from_sheet()
        allocate_reviewers(developers)
        write_reviewers_to_sheet(developers)
    except Exception as exc:
        traceback.print_exc()
        write_exception_to_sheet(str(exc) or str(type(exc)))
