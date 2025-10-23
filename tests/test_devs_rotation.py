import random
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


@patch("lib.env_constants.EXPERIENCED_DEV_NAMES", {"C", "E"})
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


@patch("lib.env_constants.EXPERIENCED_DEV_NAMES", {"Dev2", "Dev3", "Dev4", "Dev5", "Dev6", "Dev7", "Dev8", "Dev9", "Dev10"})
def test_allocate_reviewers_realistic_scenario() -> None:
    """
    Test with realistic scenario from the actual sheet.
    Non-experienced: Dev1, Dev11, Dev12
    Experienced: Dev2-Dev10 (9 developers)
    """
    # Create developers based on the actual team size
    developers = [
        Developer(name="Dev1", reviewer_number=2),
        Developer(name="Dev2", reviewer_number=2),
        Developer(name="Dev3", reviewer_number=2),
        Developer(name="Dev4", reviewer_number=2),
        Developer(name="Dev5", reviewer_number=2),
        Developer(name="Dev6", reviewer_number=2),
        Developer(name="Dev7", reviewer_number=2),
        Developer(name="Dev8", reviewer_number=2),
        Developer(name="Dev9", reviewer_number=2),
        Developer(name="Dev10", reviewer_number=2),
        Developer(name="Dev11", reviewer_number=2),
        Developer(name="Dev12", reviewer_number=2),
    ]

    allocate_reviewers(developers)

    experienced_devs = {
        "Dev2", "Dev3", "Dev4", "Dev5",
        "Dev6", "Dev7", "Dev8", "Dev9", "Dev10"
    }
    non_experienced_devs = {"Dev1", "Dev11", "Dev12"}

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
            # Non-experienced devs (Dev1, Dev11, Dev12) can
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


@patch("lib.env_constants.EXPERIENCED_DEV_NAMES", {"Dev2", "Dev3", "Dev4", "Dev5", "Dev6", "Dev7", "Dev8", "Dev9", "Dev10"})
def test_allocate_reviewers_multiple_iterations() -> None:
    """
    Run allocation 50 times with different random seeds to ensure
    the experience-based rules are ALWAYS enforced, not just by luck.
    This validates the logic is deterministically correct.
    """
    experienced_devs = {
        "Dev2", "Dev3", "Dev4", "Dev5",
        "Dev6", "Dev7", "Dev8", "Dev9", "Dev10"
    }
    non_experienced_devs = {"Dev1", "Dev11", "Dev12"}

    # Run 50 iterations with different random seeds
    for iteration in range(50):
        # Set different random seed for each iteration
        random.seed(iteration)

        # Create fresh developers for each iteration
        developers = [
            Developer(name="Dev1", reviewer_number=2),
            Developer(name="Dev2", reviewer_number=2),
            Developer(name="Dev3", reviewer_number=2),
            Developer(name="Dev4", reviewer_number=2),
            Developer(name="Dev5", reviewer_number=2),
            Developer(name="Dev6", reviewer_number=2),
            Developer(name="Dev7", reviewer_number=2),
            Developer(name="Dev8", reviewer_number=2),
            Developer(name="Dev9", reviewer_number=2),
            Developer(name="Dev10", reviewer_number=2),
            Developer(name="Dev11", reviewer_number=2),
            Developer(name="Dev12", reviewer_number=2),
        ]

        allocate_reviewers(developers)

        # Validate rules for every developer in every iteration
        for dev in developers:
            reviewer_names = dev.reviewer_names
            is_experienced = dev.name in experienced_devs

            # Must have at least 1 reviewer
            assert len(reviewer_names) >= 1, \
                f"Iteration {iteration}: {dev.name} has no reviewers"

            # No self-review
            assert dev.name not in reviewer_names, \
                f"Iteration {iteration}: {dev.name} reviewing themselves"

            # Must have at least 1 experienced reviewer
            exp_reviewers = reviewer_names & experienced_devs
            assert len(exp_reviewers) >= 1, \
                f"Iteration {iteration}: {dev.name} has no exp reviewer"

            if not is_experienced:
                # CRITICAL: Non-experienced devs can ONLY have
                # experienced reviewers
                assert reviewer_names.issubset(experienced_devs), \
                    f"Iteration {iteration}: Non-exp {dev.name} has " \
                    f"non-exp reviewers: {reviewer_names}"

                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) == 0, \
                    f"Iteration {iteration}: Non-exp {dev.name} has " \
                    f"non-exp reviewers: {non_exp_reviewers}"
            else:
                # Experienced devs can have at most 1 non-experienced
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) <= 1, \
                    f"Iteration {iteration}: Exp {dev.name} has >1 " \
                    f"non-exp: {non_exp_reviewers}"

    # Reset random seed to avoid affecting other tests
    random.seed()


@patch("lib.env_constants.EXPERIENCED_DEV_NAMES", {"ExpA", "ExpB"})
def test_allocate_reviewers_minimal_constrained_scenario() -> None:
    """
    Minimal scenario with tight constraints - runs 100 times.
    2 experienced devs, 3 non-experienced devs.
    This makes it very hard to pass "by luck" - the logic MUST
    enforce rules correctly.

    Non-experienced devs need 2 reviewers but can only get ExpA/ExpB.
    If logic is broken, it would try to assign non-exp to non-exp.
    """
    experienced_devs = {"ExpA", "ExpB"}
    non_experienced_devs = {"NonExpA", "NonExpB", "NonExpC"}

    for iteration in range(100):
        random.seed(iteration)

        # Minimal developer list - tight constraints
        developers = [
            Developer(name="ExpA", reviewer_number=2),
            Developer(name="ExpB", reviewer_number=2),
            Developer(name="NonExpA", reviewer_number=2),
            Developer(name="NonExpB", reviewer_number=2),
            Developer(name="NonExpC", reviewer_number=2),
        ]

        allocate_reviewers(developers)

        for dev in developers:
            reviewer_names = dev.reviewer_names
            is_experienced = dev.name in experienced_devs

            assert len(reviewer_names) >= 1, \
                f"Iter {iteration}: {dev.name} has no reviewers"
            assert dev.name not in reviewer_names, \
                f"Iter {iteration}: {dev.name} reviewing self"

            # Must have at least 1 experienced reviewer
            exp_reviewers = reviewer_names & experienced_devs
            assert len(exp_reviewers) >= 1, \
                f"Iter {iteration}: {dev.name} has no exp reviewer"

            if not is_experienced:
                # CRITICAL: Non-exp can ONLY have experienced reviewers
                # With only 2 exp devs available, this is very constrained
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) == 0, \
                    f"Iter {iteration}: Non-exp {dev.name} has " \
                    f"non-exp reviewers {non_exp_reviewers} - " \
                    f"LOGIC BROKEN! Should only have exp reviewers."

                assert reviewer_names.issubset(experienced_devs), \
                    f"Iter {iteration}: Non-exp {dev.name} has " \
                    f"invalid reviewers: {reviewer_names}. " \
                    f"Expected subset of {experienced_devs}"
            else:
                # Experienced devs: at most 1 non-experienced
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) <= 1, \
                    f"Iter {iteration}: Exp {dev.name} has " \
                    f"{len(non_exp_reviewers)} non-exp reviewers: " \
                    f"{non_exp_reviewers}. Maximum allowed is 1."

    random.seed()


@patch("lib.env_constants.EXPERIENCED_DEV_NAMES", {"ExpA", "ExpB"})
def test_allocate_reviewers_extreme_minimal_scenario() -> None:
    """
    Extreme minimal scenario - the ultimate stress test!
    2 experienced devs, 2 non-experienced devs, each needs 1 reviewer.

    This is the smallest possible valid configuration (need 2+ exp devs
    so they can review each other and satisfy the golden rule).

    If the logic is broken, it will fail immediately because:
    - NonExpA and NonExpB can ONLY get ExpA or ExpB
    - If logic tries to assign NonExpA to NonExpB, test fails
    - Runs 200 times to ensure it's not luck

    This configuration has near-ZERO room for error.
    """
    experienced_devs = {"ExpA", "ExpB"}
    non_experienced_devs = {"NonExpA", "NonExpB"}

    for iteration in range(200):
        random.seed(iteration)

        # Absolute minimum configuration
        developers = [
            Developer(name="ExpA", reviewer_number=1),
            Developer(name="ExpB", reviewer_number=1),
            Developer(name="NonExpA", reviewer_number=1),
            Developer(name="NonExpB", reviewer_number=1),
        ]

        allocate_reviewers(developers)

        for dev in developers:
            reviewer_names = dev.reviewer_names
            is_experienced = dev.name in experienced_devs

            # Basic validation
            assert len(reviewer_names) >= 1, \
                f"Iter {iteration}: {dev.name} has no reviewers"
            assert dev.name not in reviewer_names, \
                f"Iter {iteration}: {dev.name} reviewing self"

            # Must have at least 1 experienced reviewer
            exp_reviewers = reviewer_names & experienced_devs
            assert len(exp_reviewers) >= 1, \
                f"Iter {iteration}: {dev.name} missing exp reviewer"

            if not is_experienced:
                # THE CRITICAL TEST: Non-exp can ONLY have exp reviewers
                # They can only get ExpA or ExpB, nothing else
                assert reviewer_names.issubset(experienced_devs), \
                    f"Iter {iteration}: LOGIC ERROR! {dev.name} " \
                    f"got {reviewer_names}, expected subset of " \
                    f"{experienced_devs}. Non-exp devs can ONLY get " \
                    f"experienced reviewers!"

                # Double-check: NO non-experienced reviewers
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) == 0, \
                    f"Iter {iteration}: CRITICAL BUG! {dev.name} " \
                    f"has non-exp reviewer(s): {non_exp_reviewers}"
            else:
                # Exp can have at most 1 non-experienced
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) <= 1, \
                    f"Iter {iteration}: Exp has too many non-exp: " \
                    f"{non_exp_reviewers}"

    random.seed()
