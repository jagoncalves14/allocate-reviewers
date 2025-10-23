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


@patch.dict(os.environ, {"EXPERIENCED_DEV_NAMES": "C, E"})
def test_allocate_reviewers(mocked_devs: List[Developer]) -> None:
    """
    Test allocation with experience-based rules:
    - Non-experienced devs can ONLY have experienced reviewers
    - Experienced devs must have at least 1 experienced reviewer
      and can have at most 1 non-experienced reviewer
    """
    allocate_reviewers(mocked_devs)

    experienced_devs = {"C", "E"}

    for dev in mocked_devs:
        reviewer_names = dev.reviewer_names
        is_experienced = dev.name in experienced_devs

        # Basic validation
        assert len(reviewer_names) >= 1, \
            f"{dev.name} should have at least 1 reviewer"
        assert dev.name not in reviewer_names, \
            f"{dev.name} should not review themselves"

        # Must have at least 1 experienced reviewer
        experienced_reviewers = reviewer_names & experienced_devs
        assert len(experienced_reviewers) >= 1, \
            f"{dev.name} must have at least 1 experienced reviewer"

        if not is_experienced:
            # Non-experienced devs can ONLY have experienced reviewers
            assert reviewer_names.issubset(experienced_devs), \
                f"Non-exp dev {dev.name} can only have exp reviewers, " \
                f"got {reviewer_names}"
        else:
            # Experienced devs can have at most 1 non-experienced reviewer
            non_experienced_reviewers = reviewer_names - experienced_devs
            assert len(non_experienced_reviewers) <= 1, \
                f"Exp dev {dev.name} can have at most 1 non-exp, " \
                f"got {non_experienced_reviewers}"


@patch.dict(os.environ, {"EXPERIENCED_DEV_NAMES": "Pasha, Joao, Pawel, Robert, Damian, Chris, Kissu, Claudiu, Ximo"})
def test_allocate_reviewers_realistic_scenario() -> None:
    """
    Test with realistic scenario from the actual sheet.
    Non-experienced: Shanna, Dawid, Joseph
    Experienced: All others
    """
    # Create developers based on the actual sheet
    developers = [
        Developer(name="Shanna", reviewer_number=2),
        Developer(name="Pasha", reviewer_number=2),
        Developer(name="Joao", reviewer_number=2),
        Developer(name="Pawel", reviewer_number=2),
        Developer(name="Robert", reviewer_number=2),
        Developer(name="Damian", reviewer_number=2),
        Developer(name="Chris", reviewer_number=2),
        Developer(name="Kissu", reviewer_number=2),
        Developer(name="Claudiu", reviewer_number=2),
        Developer(name="Ximo", reviewer_number=2),
        Developer(name="Dawid", reviewer_number=2),
        Developer(name="Joseph", reviewer_number=2),
    ]

    allocate_reviewers(developers)

    experienced_devs = {
        "Pasha", "Joao", "Pawel", "Robert",
        "Damian", "Chris", "Kissu", "Claudiu", "Ximo"
    }
    non_experienced_devs = {"Shanna", "Dawid", "Joseph"}

    for dev in developers:
        reviewer_names = dev.reviewer_names
        is_experienced = dev.name in experienced_devs

        # All devs must have at least 1 reviewer
        assert len(reviewer_names) >= 1, \
            f"{dev.name} should have at least 1 reviewer"

        # No self-review
        assert dev.name not in reviewer_names

        # Must have at least 1 experienced reviewer
        exp_reviewers = reviewer_names & experienced_devs
        assert len(exp_reviewers) >= 1, \
            f"{dev.name} must have at least 1 experienced reviewer"

        if not is_experienced:
            # Non-experienced devs (Shanna, Dawid, Joseph) can
            # ONLY have experienced reviewers
            assert reviewer_names.issubset(experienced_devs), \
                f"Non-exp {dev.name} can only have exp reviewers, " \
                f"got {reviewer_names}"
            # Verify no non-experienced reviewers
            non_exp_reviewers = reviewer_names & non_experienced_devs
            assert len(non_exp_reviewers) == 0, \
                f"Non-exp {dev.name} has non-exp reviewers: " \
                f"{non_exp_reviewers}"
        else:
            # Experienced devs can have at most 1 non-experienced
            non_exp_reviewers = reviewer_names & non_experienced_devs
            assert len(non_exp_reviewers) <= 1, \
                f"Exp {dev.name} can have at most 1 non-exp, " \
                f"got {non_exp_reviewers}"
