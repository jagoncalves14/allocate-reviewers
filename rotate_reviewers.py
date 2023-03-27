import math
import traceback
from typing import List

from allocate_reviewers import (
    get_remote_sheet,
    load_developers_from_sheet,
    write_exception_to_sheet,
    write_reviewers_to_sheet,
)
from data_types import Developer
from env_constants import EXPECTED_HEADERS, REVIEWERS_CONFIG_LIST


def arrange_developers(devs: List[Developer]) -> None:
    for dev in devs:
        matched_name = next(name for name in REVIEWERS_CONFIG_LIST if name == dev.name)
        order = REVIEWERS_CONFIG_LIST.index(matched_name)
        dev.order = order


def get_previous_allocation() -> dict[str, str]:
    with get_remote_sheet() as sheet:
        developer_names = sheet.col_values(1)
        previous_allocation_ = sheet.col_values(len(EXPECTED_HEADERS) + 1)

    if not previous_allocation_:
        return {}

    if len(developer_names) != len(previous_allocation_):
        return {}

    developer_names.pop(0)
    previous_allocation_.pop(0)
    result = dict(zip(developer_names, previous_allocation_))
    return result


def add_preferable_reviewers(devs: List[Developer]) -> None:
    for dev in devs:
        if not dev.preferable_reviewer_names:
            continue

        for preferable_name in dev.preferable_reviewer_names:
            preferable_reviewer = next(
                dev_ for dev_ in devs if dev_.name == preferable_name
            )
            dev.reviewer_names.add(preferable_name)
            preferable_reviewer.review_for.add(dev.name)


def rotate_reviewers(devs: List[Developer], previous_allocation_: dict) -> None:
    """
    Assign reviewers to input developers.
    The function mutate directly the input argument "devs".
    """
    maximum_assignment = math.ceil(
        sum(dev_.reviewer_number for dev_ in devs) // len(devs)
    )

    devs.sort(key=lambda dev_: dev_.order, reverse=False)
    previous_reviewer_names_of_first_dev = previous_allocation_.get(
        devs[0].name, ""
    ).split(", ")
    order_of_previous_reviewer_names_of_first_dev = list(
        map(
            lambda reviewer_name: next(
                dev_ for dev_ in devs if dev_.name == reviewer_name
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
        skip = 0
        index = None
        remaining_reviewer_number = max(
            0, dev.reviewer_number - len(dev.reviewer_names)
        )
        for review_number in range(1, remaining_reviewer_number + 1):
            current_skip = skip

            def get_safe_numbers(skip_):
                index_ = starting_index + review_number + skip_
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
            reviewer.review_for.add(dev.name)

        if index is not None:
            starting_index = index - 1


if __name__ == "__main__":
    try:
        developers = load_developers_from_sheet()
        arrange_developers(developers)
        add_preferable_reviewers(developers)
        previous_allocation = get_previous_allocation()
        rotate_reviewers(developers, previous_allocation)
        write_reviewers_to_sheet(developers)
    except Exception as exc:
        traceback.print_exc()
        write_exception_to_sheet(str(exc) or str(type(exc)))
