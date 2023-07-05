import math
import traceback
from typing import List
from datetime import datetime

from utilities import (
    get_remote_sheet,
    write_exception_to_sheet,
    load_developers_from_sheet,
)
from data_types import Developer
from env_constants import (
    EXPECTED_HEADERS_FOR_ROTATION,
    REVIEWERS_CONFIG_LIST,
    DEFAULT_REVIEWER_NUMBER,
    ALLOCATION_INDEXES_HEADER,
    REVIEWER_NUMBER_HEADER,
    DEVELOPER_HEADER,
)


def arrange_developers(devs: List[Developer]) -> None:
    for dev in devs:
        matched_name = next(name for name in REVIEWERS_CONFIG_LIST if name == dev.name)
        order = REVIEWERS_CONFIG_LIST.index(matched_name)
        dev.order = order


def get_previous_allocation_indexes() -> dict[str, str]:
    with get_remote_sheet() as sheet:
        developer_names = sheet.col_values(1)
        allocation_indexes_ = sheet.col_values(len(EXPECTED_HEADERS_FOR_ROTATION))

    if not allocation_indexes_:
        return {}

    if len(developer_names) != len(allocation_indexes_):
        return {}

    developer_names.pop(0)
    allocation_indexes_.pop(0)
    result = dict(zip(developer_names, allocation_indexes_))
    return result


def rotate_reviewers(devs: List[Developer], allocation_indexes_: dict) -> None:
    """
    Assign reviewers to input developers.
    The function mutate directly the input argument "devs".
    """
    maximum_assignment = math.ceil(
        sum(dev_.reviewer_number for dev_ in devs) // len(devs)
    )

    devs.sort(key=lambda dev_: dev_.order, reverse=False)
    previous_allocation_indexes_of_first_dev = allocation_indexes_.get(
        devs[0].name, ""
    ).split(", ")
    try:
        previous_allocation_indexes_of_first_dev = list(
            map(lambda index_: int(index_), previous_allocation_indexes_of_first_dev)
        )
        starting_index = max(previous_allocation_indexes_of_first_dev)
    except ValueError:
        starting_index = 0

    for dev in devs:
        dev.reviewer_indexes = set()
        skip = 0
        index = None
        remaining_reviewer_number = max(
            0, dev.reviewer_number - len(dev.reviewer_names)
        )
        for review_number_index in range(0, remaining_reviewer_number):
            current_skip = skip

            def get_safe_numbers(skip_):
                index_ = starting_index + review_number_index + skip_
                safe_index_ = index_ % len(devs)
                if (
                    devs[safe_index_].name == dev.name
                    or devs[safe_index_].name in dev.reviewer_names
                ):
                    return get_safe_numbers(skip_ + 1)

                if len(
                    devs[safe_index_].review_for
                ) >= maximum_assignment and skip_ - current_skip < len(devs):
                    return get_safe_numbers(skip_ + 1)

                return safe_index_, index_, skip_

            safe_index, index, skip = get_safe_numbers(skip)
            reviewer = devs[safe_index]
            dev.reviewer_names.add(reviewer.name)
            dev.reviewer_indexes.add(str(index))
            reviewer.review_for.add(dev.name)

        if index is not None:
            starting_index = index - 1


def write_reviewers_to_sheet(devs: List[Developer]) -> None:
    allocation_column_index = len(EXPECTED_HEADERS_FOR_ROTATION)
    reviewers_column_index = allocation_column_index + 1
    allocation_column = [ALLOCATION_INDEXES_HEADER]
    reviewers_column_header = datetime.now().strftime("%d-%m-%Y")
    reviewers_column = [reviewers_column_header]

    with get_remote_sheet() as sheet:
        records = sheet.get_all_records(expected_headers=EXPECTED_HEADERS_FOR_ROTATION)
        for record in records:
            developer = next(dev for dev in devs if dev.name == record["Developer"])
            reviewer_indexes = ", ".join(sorted(developer.reviewer_indexes))
            allocation_column.append(reviewer_indexes)

            reviewer_names = ", ".join(sorted(developer.reviewer_names))
            reviewers_column.append(reviewer_names)

        sheet.delete_columns(allocation_column_index)
        sheet.insert_cols([allocation_column], allocation_column_index)
        sheet.insert_cols([reviewers_column], reviewers_column_index)


if __name__ == "__main__":
    try:
        developers = load_developers_from_sheet(
            EXPECTED_HEADERS_FOR_ROTATION,
            values_mapper=lambda record: Developer(
                name=record[DEVELOPER_HEADER],
                reviewer_number=int(
                    record[REVIEWER_NUMBER_HEADER] or DEFAULT_REVIEWER_NUMBER
                ),
                reviewer_indexes=set((record[ALLOCATION_INDEXES_HEADER]).split(", "))
                if record[ALLOCATION_INDEXES_HEADER]
                else set(),
            ),
        )
        arrange_developers(developers)
        allocation_indexes = get_previous_allocation_indexes()
        rotate_reviewers(developers, allocation_indexes)
        write_reviewers_to_sheet(developers)
    except Exception as exc:
        traceback.print_exc()
        write_exception_to_sheet(
            EXPECTED_HEADERS_FOR_ROTATION, str(exc) or str(type(exc))
        )
