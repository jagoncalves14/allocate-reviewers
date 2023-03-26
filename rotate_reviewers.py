import traceback
from typing import List

import gspread
from dotenv import find_dotenv, load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

from allocate_reviewers import (
    get_remote_sheet,
    load_developers_from_sheet,
    write_exception_to_sheet,
    write_reviewers_to_sheet,
)
from data_types import Developer
from env_constants import EXPECTED_HEADERS, REVIEWERS_CONFIG_LIST

load_dotenv(find_dotenv())


def arrange_developers(devs: List[Developer]) -> None:
    for dev in devs:
        matched_name = next(name for name in REVIEWERS_CONFIG_LIST if name == dev.name)
        order = REVIEWERS_CONFIG_LIST.index(matched_name)
        dev.order = order


def get_previous_allocation() -> dict[str, str]:
    with get_remote_sheet() as sheet:
        developer_names = sheet.col_values(1)
        previous_allocation = sheet.col_values(len(EXPECTED_HEADERS) + 1)

    if not previous_allocation:
        return {}

    developer_names.pop(0)
    previous_allocation.pop(0)
    result = dict(zip(developer_names, previous_allocation))
    return result


def rotate_reviewers(devs: List[Developer], previous_allocation: dict) -> None:
    """
    Assign reviewers to input developers.
    The function mutate directly the input argument "devs".
    """
    devs.sort(key=lambda dev: dev.order, reverse=False)
    previous_reviewer_names_of_first_dev = previous_allocation.get(
        devs[0].name, ""
    ).split(", ")
    order_of_previous_reviewer_names_of_first_dev = list(
        map(
            lambda reviewer_name: next(
                dev for dev in devs if dev.name == reviewer_name
            ).order,
            previous_reviewer_names_of_first_dev,
        )
    )
    starting_index = (
        max(order_of_previous_reviewer_names_of_first_dev)
        if order_of_previous_reviewer_names_of_first_dev
        else 0
    )
    for dev in devs:
        overlap = 0
        for review_number in range(1, dev.reviewer_number + 1):
            index = starting_index + review_number + overlap
            safe_index = index % len(devs)
            # Maximum 1 overlap (developer's name == reviewer's name) per dev per run.
            if dev.name == devs[safe_index].name:
                overlap += 1
                index = starting_index + review_number + overlap
                safe_index = index % len(devs)

            reviewer = devs[safe_index]
            dev.reviewer_names.add(reviewer.name)
            reviewer.review_for.add(dev.name)

        starting_index = index - 1


if __name__ == "__main__":
    try:
        developers = load_developers_from_sheet()
        arrange_developers(developers)
        previous_allocation = get_previous_allocation()
        rotate_reviewers(developers, previous_allocation)
        write_reviewers_to_sheet(developers)
    except Exception as exc:
        traceback.print_exc()
        write_exception_to_sheet(str(exc) or str(type(exc)))
