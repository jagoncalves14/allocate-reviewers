import os
from typing import List, Set
from unittest.mock import patch

import pytest

from allocate_reviewers import (
    Developer,
    allocate_reviewers,
    shuffle_and_get_the_most_available_names,
)
from tests.conftest import DEVS
from tests.utils import mutate_devs


@pytest.mark.parametrize(
    "available_names,number_of_names,expected",
    [
        (set(("A", "B")), 0, []),
        (set(dev.name for dev in DEVS), 2, ["A", "E"]),
    ],
    ids=[
        "Number of names is 0",
        "Based on assigned times",
    ],
)
def test_shuffle_and_get_the_most_available_names(
    available_names: Set[str],
    number_of_names: int,
    expected: List[str],
    mocked_devs: List[Developer],
) -> None:
    DEV_REVIEW_LIST_MAPPER = {
        "B": set(("C", "D")),
        "C": set(("A", "B")),
        "D": set("E"),
    }
    mutate_devs(mocked_devs, "review_for", DEV_REVIEW_LIST_MAPPER)

    assert (
        shuffle_and_get_the_most_available_names(
            available_names, number_of_names, mocked_devs
        )
        == expected
    )


@patch.dict(os.environ, {"EXPERIENCED_DEV_NAMES": "E"})
def test_allocate_reviewers(mocked_devs: List[Developer]) -> None:
    allocate_reviewers(mocked_devs)

    # By preference:
    reviewer_names = mocked_devs[0].reviewer_names
    assert len(reviewer_names) == 1
    assert list(reviewer_names)[0] in mocked_devs[0].preferable_reviewer_names

    for dev in mocked_devs[1:]:
        expected_reviewer_number = min(dev.reviewer_number, len(mocked_devs) - 1)
        reviewer_names = dev.reviewer_names

        assert len(reviewer_names) == expected_reviewer_number
        assert dev.name not in reviewer_names
        if dev.name == "E":
            continue

        assert "E" in reviewer_names
