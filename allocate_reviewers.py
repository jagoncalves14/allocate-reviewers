import os
import random
import traceback
from typing import List, Set
from datetime import datetime

from dotenv import find_dotenv, load_dotenv

from data_types import Developer, SelectableConfigure
from env_constants import (
    EXPECTED_HEADERS_FOR_ALLOCATION,
)
from utilities import (
    load_developers_from_sheet,
    write_exception_to_sheet,
    get_remote_sheet,
)

load_dotenv(find_dotenv())


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
        key=lambda name: len(
            next(dev for dev in devs if dev.name == name).review_for
        ),
    )

    return names[0:number_of_names]


def allocate_reviewers(devs: List[Developer]) -> None:
    """
    Assign reviewers to input developers.
    The function mutate directly the input argument "devs".
    """
    experienced_dev_names = set(
        os.environ.get("EXPERIENCED_DEV_NAMES", "").split(", ")
    )

    all_dev_names = set((dev.name for dev in devs))
    valid_experienced_dev_names = set(
        (name for name in experienced_dev_names if name in all_dev_names)
    )

    # To process devs with preferable_reviewer_names first.
    devs.sort(key=lambda dev: dev.preferable_reviewer_names, reverse=True)

    for dev in devs:
        chosen_reviewer_names: Set[str] = set()
        reviewer_number = min(dev.reviewer_number, len(all_dev_names) - 1)

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
                names=dev.preferable_reviewer_names,
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
                    if name not in [dev.name, *chosen_reviewer_names]
                )
            )
            selectable_number = configure.number_getter()
            chosen_names = shuffle_and_get_the_most_available_names(
                selectable_names, selectable_number, devs
            )
            chosen_reviewer_names.update(chosen_names)

        reviewers = (dev for dev in devs if dev.name in chosen_reviewer_names)
        for reviewer in reviewers:
            dev.reviewer_names.add(reviewer.name)
            reviewer.review_for.add(dev.name)


def write_reviewers_to_sheet(devs: List[Developer]) -> None:
    column_index = len(EXPECTED_HEADERS_FOR_ALLOCATION) + 1
    column_header = datetime.now().strftime("%d-%m-%Y")
    new_column = [column_header]

    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(
            expected_headers=EXPECTED_HEADERS_FOR_ALLOCATION
        )
        for record in records:
            developer = next(
                dev for dev in devs if dev.name == record["Developer"]
            )
            reviewer_names = ", ".join(
                sorted(developer.reviewer_names)
            )
            new_column.append(reviewer_names)
        sheet.insert_cols([new_column], column_index)


if __name__ == "__main__":
    try:
        developers = load_developers_from_sheet(EXPECTED_HEADERS_FOR_ALLOCATION)
        allocate_reviewers(developers)

        # Manual runs update existing column, scheduled runs create new column
        is_manual = os.environ.get("MANUAL_RUN", "").lower() == "true"
        if is_manual:
            print("Manual run: Updating current sprint column")
            update_current_sprint_reviewers(developers)
        else:
            print("Scheduled run: Creating new sprint column")
            write_reviewers_to_sheet(developers)
    except Exception as exc:
        traceback.print_exc()
        write_exception_to_sheet(
            EXPECTED_HEADERS_FOR_ALLOCATION, str(exc) or str(type(exc))
        )
