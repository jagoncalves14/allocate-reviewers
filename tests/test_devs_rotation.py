import os
from typing import List, Set
from unittest.mock import patch

import pytest

from scripts.rotate_devs_reviewers import (
    allocate_reviewers,
    shuffle_and_get_the_most_available_names,
)
from lib.data_types import Developer
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
    chosen_names = shuffle_and_get_the_most_available_names(
        available_names, number_of_names, mocked_devs
    )
    assert sorted(chosen_names) == sorted(expected)


@patch.dict(os.environ, {"EXPERIENCED_DEV_NAMES": "E"})
def test_allocate_reviewers(mocked_devs: List[Developer]) -> None:
    allocate_reviewers(mocked_devs)

    # Developer A wants 1 reviewer and prefers B, C
    # But must have at least 1 experienced dev (E)
    # So if preferable reviewer is picked (B or C), E is added too
    reviewer_names = mocked_devs[0].reviewer_names
    # Should have at least 1 reviewer
    assert len(reviewer_names) >= 1
    # Must include experienced dev E
    assert "E" in reviewer_names

    for dev in mocked_devs[1:]:
        expected_reviewer_number = min(dev.reviewer_number, len(mocked_devs) - 1)
        reviewer_names = dev.reviewer_names

        # Should have at least the expected number (might be more due to experienced req)
        assert len(reviewer_names) >= expected_reviewer_number
        assert dev.name not in reviewer_names
        if dev.name == "E":
            continue

        # All non-E devs must have E as a reviewer
        assert "E" in reviewer_names
