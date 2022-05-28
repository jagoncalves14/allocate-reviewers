import math
import random
import pprint
import gspread
from typing import List
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, field
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials


SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]
CREDENTIAL_FILE = "client_key.json"
SHEET_NAME = "R"
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


@contextmanager
def get_remote_sheet() -> Worksheet:
    credential = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIAL_FILE, SCOPE
    )
    client = gspread.authorize(credential)
    sheet = client.open(SHEET_NAME).sheet1
    yield sheet
    client.session.close()


def load_data() -> List[Developer]:
    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(expected_headers=EXPECTED_HEADERS)

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
            if reviewer_number < len(preferable_reviewers):
                preferable_reviewers = random.sample(
                    preferable_reviewers, reviewer_number
                )
            return [dev for dev in devs if dev.name in preferable_reviewers]

        fist_available_reviewers = [
            dev
            for dev in devs
            if dev.name != dev_name
            and len(dev.review_for) < max(maximum_review_times - 1, 1)
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

    # To process devs with preferable_reviewers first.
    devs.sort(key=lambda dev: not dev.preferable_reviewers)
    for dev in devs:
        reviewers = get_reviewers(
            dev.name, dev.reviewer_number, dev.preferable_reviewers
        )
        for reviewer in reviewers:
            dev.reviewers.append(reviewer.name)
            reviewer.review_for.append(dev.name)


def update_data(devs: List[Developer]) -> None:
    col_index = len(EXPECTED_HEADERS) + 1
    col_header = datetime.now().strftime("%d-%m-%Y")
    update_column = [col_header]

    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(expected_headers=EXPECTED_HEADERS)
        for record in records:
            developer = next(dev for dev in devs if dev.name == record["Developer"])
            reviewers = ", ".join(reviewer for reviewer in developer.reviewers)
            update_column.append(reviewers)
        sheet.insert_cols([update_column], col_index)


def write_exception(error: str) -> None:
    col_index = len(EXPECTED_HEADERS) + 1
    update_column = [f"Exception {datetime.now().strftime('%d-%m-%Y')}", error]
    with get_remote_sheet() as sheet:
        sheet.insert_cols([update_column], col_index)


if __name__ == "__main__":
    try:
        developers = load_data()
        allocate_reviewers(developers)
        # pp.pprint("Allocating results:")
        # pp.pprint(developers)
        update_data(developers)
    except Exception as exc:
        write_exception(str(exc))
