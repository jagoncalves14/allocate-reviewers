import os
import random
import gspread
from dotenv import load_dotenv, find_dotenv
from typing import List, Set
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, field
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv(find_dotenv())

CREDENTIAL_FILE = os.environ.get("CREDENTIAL_FILE")
SHEET_NAME = os.environ.get("SHEET_NAME")
MINIMUM_REVIEWER_NUMBER = int(os.environ.get("MINIMUM_REVIEWER_NUMBER"))
EXPERIENCED_DEV_NAMES = set(os.environ.get("EXPERIENCED_DEV_NAMES").split(", "))

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


@contextmanager
def get_remote_sheet() -> Worksheet:
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

    input_developers = list()
    for record in records:
        developer = Developer(
            name=record["Developer"],
            reviewer_number=record["Reviewer Number"] or MINIMUM_REVIEWER_NUMBER,
            preferable_reviewer_names=set(record["Preferable Reviewers"].split(", "))
            if record["Preferable Reviewers"]
            else set(),
        )
        input_developers.append(developer)

    return input_developers


def allocate_reviewers(devs: List[Developer]) -> None:
    """
    Assign reviewers to input developers.
    The function mutate directly the input argument "devs".
    """

    def shuffle_and_get_the_most_available_names_for(
        dev_name, available_names, number_of_names
    ):
        """
        Parameters:
            dev_name (str): Name of the developer
            available_names (Set[str]): List of available names
            number_of_names (int): Number of names to get
        Returns:
            (List[str]): A list of reviewer names for the developer from available names.
        """
        if number_of_names == 0:
            return []

        selectable_names = [name for name in available_names if name and name != dev_name]
        if 0 == len(selectable_names) <= number_of_names:
            return selectable_names

        random.shuffle(selectable_names)
        selectable_names.sort(
            key=lambda name: len(
                next(dev for dev in devs if dev.name == name).review_for
            ),
        )

        return selectable_names[0:number_of_names]

    # To process devs with preferable_reviewer_names first.
    devs.sort(key=lambda dev: dev.preferable_reviewer_names, reverse=True)
    for dev in devs:
        reviewer_number = dev.reviewer_number
        preferable_reviewer_names = dev.preferable_reviewer_names.copy()
        chosen_reviewer_names = set()

        chosen_names = shuffle_and_get_the_most_available_names_for(
            dev.name, preferable_reviewer_names, reviewer_number
        )
        chosen_reviewer_names.update(chosen_names)
        reviewer_number = max(reviewer_number - len(chosen_names), 0)

        prior_names = [
            name for name in EXPERIENCED_DEV_NAMES if name not in chosen_reviewer_names
        ]
        chosen_names = shuffle_and_get_the_most_available_names_for(
            dev.name, prior_names, 1
        )
        chosen_reviewer_names.update(chosen_names)
        reviewer_number = max(reviewer_number - len(chosen_names), 0)

        available_reviewer_names = [
            dev.name for dev in devs if dev.name not in chosen_reviewer_names
        ]
        chosen_names = shuffle_and_get_the_most_available_names_for(
            dev.name, available_reviewer_names, reviewer_number
        )
        chosen_reviewer_names.update(chosen_names)

        reviewers = [dev for dev in devs if dev.name in chosen_reviewer_names]
        for reviewer in reviewers:
            dev.reviewer_names.add(reviewer.name)
            reviewer.review_for.add(dev.name)


def write_reviewers_to_sheet(devs: List[Developer]) -> None:
    column_index = len(EXPECTED_HEADERS) + 1
    column_header = datetime.now().strftime("%d-%m-%Y")
    new_column = [column_header]

    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(expected_headers=EXPECTED_HEADERS)
        for record in records:
            developer = next(dev for dev in devs if dev.name == record["Developer"])
            reviewer_names = ", ".join(developer.reviewer_names)
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
        write_exception_to_sheet(str(exc))
