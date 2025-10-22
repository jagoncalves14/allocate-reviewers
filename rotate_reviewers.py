"""
Rotate developers as reviewers for each developer in the list.
For each rotation, each developer has other developers assigned as reviewers, 
among which there is at least 1 senior reviewer.
The new rotation result should be different from the previous one.
"""

import math
import traceback
from typing import List
from datetime import datetime, timezone

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


def get_previous_allocation_indexes() -> dict[str, list]:
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

    for dev_name, dev_allocated_indexes in result.items():
        dev_allocated_indexes = dev_allocated_indexes.split(", ")
        result[dev_name] = list(map(lambda index_: int(index_), dev_allocated_indexes))

    return result


def rotate_reviewers(devs: List[Developer], allocation_indexes_: dict) -> None:
    """
    Assign reviewers to input developers ensuring:
    - At least 1 senior reviewer per developer
    - Different rotation from previous assignments
    - Respect developer's requested reviewer_number property
    """
    from env_constants import EXPERIENCED_DEV_NAMES

    # Calculate maximum assignments based on average reviewer_number
    total_reviewer_number = sum(dev.reviewer_number for dev in devs)
    maximum_assignment = math.ceil(total_reviewer_number / len(devs))

    devs.sort(key=lambda dev_: dev_.order, reverse=False)

    def find_reviewer(
        starting_index: int, dev: Developer, must_be_senior: bool = False, skip: int = 1
    ) -> tuple[int, int, int]:
        index_ = starting_index + skip
        safe_index_ = index_ % len(devs)
        reviewer = devs[safe_index_]

        is_invalid = (
            reviewer.name == dev.name
            or reviewer.name in dev.reviewer_names
            or len(reviewer.review_for) >= maximum_assignment
        )

        if must_be_senior:
            is_invalid = is_invalid or reviewer.name not in EXPERIENCED_DEV_NAMES

        if is_invalid:
            return find_reviewer(starting_index, dev, must_be_senior, skip + 1)

        return safe_index_, index_, skip

    # Assign a senior reviewer to each developer
    for dev in devs:
        dev.reviewer_indexes = set()
        dev_allocated_indexes = allocation_indexes_.get(dev.name, [0])
        starting_index = max(dev_allocated_indexes)

        safe_index, index, _ = find_reviewer(starting_index, dev, must_be_senior=True)
        reviewer = devs[safe_index]
        dev.reviewer_names.add(reviewer.name)
        dev.reviewer_indexes.add(str(index))
        reviewer.review_for.add(dev.name)

    # Assign additional reviewers up to the required reviewer_number
    for dev in devs:
        while len(dev.reviewer_names) < dev.reviewer_number:
            dev_allocated_indexes = allocation_indexes_.get(dev.name, [0])

            if dev.reviewer_indexes:
                reviewer_indexes_as_ints = [int(idx) for idx in dev.reviewer_indexes]
                starting_index = max(
                    max(reviewer_indexes_as_ints), max(dev_allocated_indexes)
                )
            else:
                starting_index = max(dev_allocated_indexes)

            safe_index, index, _ = find_reviewer(starting_index, dev)
            reviewer = devs[safe_index]
            dev.reviewer_names.add(reviewer.name)
            dev.reviewer_indexes.add(str(index))
            reviewer.review_for.add(dev.name)


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
    week_number = datetime.now(timezone.utc).isocalendar().week
    if week_number % 2 != 0:
        try:
            developers = load_developers_from_sheet(
                EXPECTED_HEADERS_FOR_ROTATION,
                values_mapper=lambda record: Developer(
                    name=record[DEVELOPER_HEADER],
                    reviewer_number=int(
                        record[REVIEWER_NUMBER_HEADER] or DEFAULT_REVIEWER_NUMBER
                    ),
                    reviewer_indexes=(
                        set((record[ALLOCATION_INDEXES_HEADER]).split(", "))
                        if record[ALLOCATION_INDEXES_HEADER]
                        else set()
                    ),
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
