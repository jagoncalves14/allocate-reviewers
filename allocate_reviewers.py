import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Callable, Tuple

import gspread
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials
import pprint

SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]
CREDENTIAL_FILE = "client_key.json"
MINIMUM_REVIEWER_NUMBER = 1
EXPECTED_HEADERS = ["Developer", "Reviewer Number", "Preferable Reviewers"]
pp = pprint.PrettyPrinter()


@dataclass
class Developer:
    name: str
    reviewer_number: int
    preferable_reviewers: List[str]
    reviewers: List[str] = field(default_factory=list)
    review_for: List[str] = field(default_factory=list)


def get_remote_sheet() -> Tuple[Worksheet, Callable[[], None]]:
    """
    Returns:
        Tuple[Worksheet, Callable[[], None]]: The first worksheet and a function to close connection to GSheet.
    """
    credential = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIAL_FILE, SCOPE
    )
    client = gspread.authorize(credential)
    sheet = client.open("Reviewers").sheet1
    return sheet, lambda: client.session.close()


def load_data() -> List[Developer]:
    sheet, close_connection = get_remote_sheet()
    records = sheet.get_all_records(expected_headers=EXPECTED_HEADERS)
    close_connection()

    input_developers = list()
    for record in records:
        developer = Developer(
            name=record["Developer"],
            reviewer_number=record["Reviewer Number"] or MINIMUM_REVIEWER_NUMBER,
            preferable_reviewers=record["Preferable Reviewers"].split(", ")
            if record["Preferable Reviewers"]
            else [],
        )
        input_developers.append(developer)

    # pp.pprint(input_developers)
    return input_developers


def allocate_reviewers(devs: List[Developer]) -> None:
    maximum_review_times = math.ceil(
        sum([dev.reviewer_number for dev in devs]) / len(devs)
    )

    def get_reviewers(
        dev_name: str, reviewer_number: int, preferable_reviewers: List[str]
    ) -> List[Developer]:
        """
        Parameters:
            dev_name (str): Name of the developer
            reviewer_number (int): Number of reviewers for the developer
            preferable_reviewers (List[str]): List of preferable reviewers for the developer
        Returns:
            (List[Developer]): A list of reviewers for the developer
        """
        if preferable_reviewers:
            return [dev for dev in devs if dev.name in preferable_reviewers]

        fist_available_reviewers = [
            dev for dev in devs if dev.name != dev_name and len(dev.review_for) < max(maximum_review_times - 1, 1)
        ]
        if len(fist_available_reviewers) >= reviewer_number:
            selected_reviewers = random.sample(
                fist_available_reviewers, reviewer_number
            )
        else:
            second_available_reviewers = [
                dev
                for dev in devs
                if dev.name != dev_name
                and dev not in fist_available_reviewers
                and len(dev.review_for) < maximum_review_times
            ]
            selected_reviewers = fist_available_reviewers + random.sample(
                second_available_reviewers,
                reviewer_number - len(fist_available_reviewers),
            )

        return selected_reviewers

    for dev in devs:
        reviewers = get_reviewers(
            dev.name, dev.reviewer_number, dev.preferable_reviewers
        )
        for reviewer in reviewers:
            dev.reviewers.append(reviewer.name)
            reviewer.review_for.append(dev.name)


def update_data(devs: List[Developer]) -> None:
    sheet, close_connection = get_remote_sheet()
    records = sheet.get_all_records(expected_headers=EXPECTED_HEADERS)
    col_index = len(EXPECTED_HEADERS) + 1
    col_header = datetime.now().strftime("%d-%m-%Y")
    update_column = [col_header]
    for record in records:
        developer = next(dev for dev in devs if dev.name == record["Developer"])
        reviewers = ", ".join(reviewer for reviewer in developer.reviewers)
        update_column.append(reviewers)
    sheet.insert_cols([update_column], col_index)
    close_connection()


def write_exception(error: str) -> None:
    sheet, close_connection = get_remote_sheet()
    col_index = len(EXPECTED_HEADERS) + 1
    update_column = [f"Exception {datetime.now().strftime('%d-%m-%Y')}", error]
    sheet.insert_cols([update_column], col_index)
    close_connection()


if __name__ == "__main__":
    try:
        developers = load_data()
        allocate_reviewers(developers)
        # pp.pprint("Allocating results:")
        # pp.pprint(developers)
        update_data(developers)
    except Exception as exc:
        write_exception(str(exc))
