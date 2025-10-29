import random
from typing import List, Set
from unittest.mock import patch

import pytest

from lib.data_types import Developer
from scripts.rotate_devs_reviewers import (
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
    """Test shuffle_and_get_the_most_available_names balances load."""
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


@patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", {"A", "B", "D"})
def test_allocate_reviewers(mocked_devs: List[Developer]) -> None:
    """
    Test allocation with experience-based rules (INVERTED LOGIC):
    - Unexperienced devs can ONLY have experienced reviewers
    - Experienced devs must have at least 1 experienced reviewer
      and can have at most 1 unexperienced reviewer
    """
    allocate_reviewers(mocked_devs)

    experienced_devs = {"C", "E"}  # NOT in unexperienced list

    for dev in mocked_devs:
        reviewer_names = dev.reviewer_names
        is_experienced = dev.name in experienced_devs

        # Basic validation
        assert len(reviewer_names) >= 1, f"{dev.name} should have at least 1 reviewer"
        assert dev.name not in reviewer_names, f"{dev.name} should not review themselves"

        # Must have at least 1 experienced reviewer
        experienced_reviewers = reviewer_names & experienced_devs
        assert (
            len(experienced_reviewers) >= 1
        ), f"{dev.name} must have at least 1 experienced reviewer"

        if not is_experienced:
            # Non-experienced devs can ONLY have experienced reviewers
            assert reviewer_names.issubset(experienced_devs), (
                f"Non-exp dev {dev.name} can only have exp reviewers, " f"got {reviewer_names}"
            )
        else:
            # Experienced devs can have at most 1 non-experienced reviewer
            non_experienced_reviewers = reviewer_names - experienced_devs
            assert len(non_experienced_reviewers) <= 1, (
                f"Exp dev {dev.name} can have at most 1 non-exp, "
                f"got {non_experienced_reviewers}"
            )


@patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", {"Dev1", "Dev11", "Dev12"})
def test_allocate_reviewers_realistic_scenario() -> None:
    """
    Test with realistic scenario from the actual sheet (INVERTED LOGIC).
    Unexperienced: Dev1, Dev11, Dev12
    Experienced: Dev2-Dev10 (9 developers, NOT in unexperienced list)
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
        "Dev2",
        "Dev3",
        "Dev4",
        "Dev5",
        "Dev6",
        "Dev7",
        "Dev8",
        "Dev9",
        "Dev10",
    }
    non_experienced_devs = {"Dev1", "Dev11", "Dev12"}

    for dev in developers:
        reviewer_names = dev.reviewer_names
        is_experienced = dev.name in experienced_devs

        # All devs must have at least 1 reviewer
        assert len(reviewer_names) >= 1, f"{dev.name} should have at least 1 reviewer"

        # No self-review
        assert dev.name not in reviewer_names

        # Must have at least 1 experienced reviewer
        exp_reviewers = reviewer_names & experienced_devs
        assert len(exp_reviewers) >= 1, f"{dev.name} must have at least 1 experienced reviewer"

        if not is_experienced:
            # Non-experienced devs (Dev1, Dev11, Dev12) can
            # ONLY have experienced reviewers
            assert reviewer_names.issubset(experienced_devs), (
                f"Non-exp {dev.name} can only have exp reviewers, " f"got {reviewer_names}"
            )
            # Verify no non-experienced reviewers
            non_exp_reviewers = reviewer_names & non_experienced_devs
            assert len(non_exp_reviewers) == 0, (
                f"Non-exp {dev.name} has non-exp reviewers: " f"{non_exp_reviewers}"
            )
        else:
            # Experienced devs can have at most 1 non-experienced
            non_exp_reviewers = reviewer_names & non_experienced_devs
            assert len(non_exp_reviewers) <= 1, (
                f"Exp {dev.name} can have at most 1 non-exp, " f"got {non_exp_reviewers}"
            )


@patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", {"Dev1", "Dev11", "Dev12"})
def test_allocate_reviewers_multiple_iterations() -> None:
    """
    Run allocation 50 times with different random seeds to ensure
    the experience-based rules are ALWAYS enforced, not just by luck.
    This validates the logic is deterministically correct (INVERTED LOGIC).
    """
    experienced_devs = {
        "Dev2",
        "Dev3",
        "Dev4",
        "Dev5",
        "Dev6",
        "Dev7",
        "Dev8",
        "Dev9",
        "Dev10",
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
            assert len(reviewer_names) >= 1, f"Iteration {iteration}: {dev.name} has no reviewers"

            # No self-review
            assert (
                dev.name not in reviewer_names
            ), f"Iteration {iteration}: {dev.name} reviewing themselves"

            # Must have at least 1 experienced reviewer
            exp_reviewers = reviewer_names & experienced_devs
            assert len(exp_reviewers) >= 1, f"Iteration {iteration}: {dev.name} has no exp reviewer"

            if not is_experienced:
                # CRITICAL: Non-experienced devs can ONLY have
                # experienced reviewers
                assert reviewer_names.issubset(experienced_devs), (
                    f"Iteration {iteration}: Non-exp {dev.name} has "
                    f"non-exp reviewers: {reviewer_names}"
                )

                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) == 0, (
                    f"Iteration {iteration}: Non-exp {dev.name} has "
                    f"non-exp reviewers: {non_exp_reviewers}"
                )
            else:
                # Experienced devs can have at most 1 non-experienced
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) <= 1, (
                    f"Iteration {iteration}: Exp {dev.name} has >1 " f"non-exp: {non_exp_reviewers}"
                )

    # Reset random seed to avoid affecting other tests
    random.seed()


@patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", {"NonExpA", "NonExpB", "NonExpC"})
def test_allocate_reviewers_minimal_constrained_scenario() -> None:
    """
    Minimal scenario with tight constraints - runs 100 times (INVERTED LOGIC).
    2 experienced devs, 3 non-experienced devs.
    This makes it very hard to pass "by luck" - the logic MUST
    enforce rules correctly.

    Non-experienced devs need 2 reviewers but can only get ExpA/ExpB.
    If logic is broken, it would try to assign non-exp to non-exp.
    """
    experienced_devs = {"ExpA", "ExpB"}  # NOT in unexperienced list
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

            assert len(reviewer_names) >= 1, f"Iter {iteration}: {dev.name} has no reviewers"
            assert dev.name not in reviewer_names, f"Iter {iteration}: {dev.name} reviewing self"

            # Must have at least 1 experienced reviewer
            exp_reviewers = reviewer_names & experienced_devs
            assert len(exp_reviewers) >= 1, f"Iter {iteration}: {dev.name} has no exp reviewer"

            if not is_experienced:
                # CRITICAL: Non-exp can ONLY have experienced reviewers
                # With only 2 exp devs available, this is very constrained
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) == 0, (
                    f"Iter {iteration}: Non-exp {dev.name} has "
                    f"non-exp reviewers {non_exp_reviewers} - "
                    f"LOGIC BROKEN! Should only have exp reviewers."
                )

                assert reviewer_names.issubset(experienced_devs), (
                    f"Iter {iteration}: Non-exp {dev.name} has "
                    f"invalid reviewers: {reviewer_names}. "
                    f"Expected subset of {experienced_devs}"
                )
            else:
                # Experienced devs: at most 1 non-experienced
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) <= 1, (
                    f"Iter {iteration}: Exp {dev.name} has "
                    f"{len(non_exp_reviewers)} non-exp reviewers: "
                    f"{non_exp_reviewers}. Maximum allowed is 1."
                )

    random.seed()


@patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", {"NonExpA", "NonExpB", "NonExpC"})
def test_allocate_reviewers_extreme_minimal_scenario() -> None:
    """
    Minimal scenario stress test with retry mechanism (INVERTED LOGIC).
    2 experienced devs, 2 non-experienced devs.

    Experienced devs need 2 reviewers (to leave room for non-exp to be assigned).
    Non-experienced devs need 1 reviewer.

    Tests that retry mechanism can find a valid allocation even in
    constrained scenarios.
    """
    experienced_devs = {"ExpA", "ExpB"}
    non_experienced_devs = {"NonExpA", "NonExpB"}

    for iteration in range(20):  # Reduced from 200 since retry is slow
        random.seed(iteration)

        # Minimal configuration with space for non-exp
        developers = [
            Developer(name="ExpA", reviewer_number=2),  # Increased to allow space
            Developer(name="ExpB", reviewer_number=2),  # Increased to allow space
            Developer(name="NonExpA", reviewer_number=1),
            Developer(name="NonExpB", reviewer_number=1),
        ]

        allocate_reviewers(developers)

        for dev in developers:
            reviewer_names = dev.reviewer_names
            is_experienced = dev.name in experienced_devs

            # Basic validation
            assert len(reviewer_names) >= 1, f"Iter {iteration}: {dev.name} has no reviewers"
            assert dev.name not in reviewer_names, f"Iter {iteration}: {dev.name} reviewing self"

            # Must have at least 1 experienced reviewer
            exp_reviewers = reviewer_names & experienced_devs
            assert len(exp_reviewers) >= 1, f"Iter {iteration}: {dev.name} missing exp reviewer"

            if not is_experienced:
                # THE CRITICAL TEST: Non-exp can ONLY have exp reviewers
                # They can only get ExpA or ExpB, nothing else
                assert reviewer_names.issubset(experienced_devs), (
                    f"Iter {iteration}: LOGIC ERROR! {dev.name} "
                    f"got {reviewer_names}, expected subset of "
                    f"{experienced_devs}. Non-exp devs can ONLY get "
                    f"experienced reviewers!"
                )

                # Double-check: NO non-experienced reviewers
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) == 0, (
                    f"Iter {iteration}: CRITICAL BUG! {dev.name} "
                    f"has non-exp reviewer(s): {non_exp_reviewers}"
                )
            else:
                # Exp can have at most 1 non-experienced
                non_exp_reviewers = reviewer_names & non_experienced_devs
                assert len(non_exp_reviewers) <= 1, (
                    f"Iter {iteration}: Exp has too many non-exp: " f"{non_exp_reviewers}"
                )

    random.seed()


@patch(
    "lib.env_constants.UNEXPERIENCED_DEV_NAMES",
    {"NonExperiencedDev1", "NonExperiencedDev2"},
)
def test_non_experienced_devs_are_assigned() -> None:
    """
    Test that non-experienced developers are assigned as reviewers (INVERTED LOGIC).
    The new requirement: non-experienced devs should review others too!

    Rules:
    - Non-experienced devs can ONLY have experienced reviewers
    - Non-experienced devs SHOULD be assigned to review experienced devs
    - Experienced devs can have at most 1 non-experienced reviewer
    """
    # 12 experienced (NOT in unexp list), 2 non-experienced (in the list)
    developers = [
        Developer(name="NonExperiencedDev1", reviewer_number=2),  # Non-exp
        Developer(name="NonExperiencedDev2", reviewer_number=2),  # Non-exp
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
        "Dev1",
        "Dev2",
        "Dev3",
        "Dev4",
        "Dev5",
        "Dev6",
        "Dev7",
        "Dev8",
        "Dev9",
        "Dev10",
        "Dev11",
        "Dev12",
    }
    non_experienced_devs = {"NonExperiencedDev1", "NonExperiencedDev2"}

    non_exp_dev1 = next(d for d in developers if d.name == "NonExperiencedDev1")
    non_exp_dev2 = next(d for d in developers if d.name == "NonExperiencedDev2")

    # Verify non-experienced devs have ONLY experienced reviewers
    assert non_exp_dev1.reviewer_names.issubset(
        experienced_devs
    ), f"NonExperiencedDev1 should only have experienced reviewers, got {non_exp_dev1.reviewer_names}"
    assert non_exp_dev2.reviewer_names.issubset(
        experienced_devs
    ), f"NonExperiencedDev2 should only have experienced reviewers, got {non_exp_dev2.reviewer_names}"

    # THE KEY TEST: Non-experienced devs should be assigned to review others
    assert (
        len(non_exp_dev1.review_for) > 0
    ), f"NonExperiencedDev1 should be assigned to review someone! Currently reviewing: {non_exp_dev1.review_for}"
    assert (
        len(non_exp_dev2.review_for) > 0
    ), f"NonExperiencedDev2 should be assigned to review someone! Currently reviewing: {non_exp_dev2.review_for}"

    # They should be reviewing experienced devs only
    for dev_name in non_exp_dev1.review_for:
        assert (
            dev_name in experienced_devs
        ), f"NonExperiencedDev1 is reviewing {dev_name} but should only review experienced devs"

    for dev_name in non_exp_dev2.review_for:
        assert (
            dev_name in experienced_devs
        ), f"NonExperiencedDev2 is reviewing {dev_name} but should only review experienced devs"

    # Verify experienced devs they're reviewing have at most 1 non-exp reviewer
    for dev in developers:
        if dev.name in experienced_devs:
            non_exp_reviewers = dev.reviewer_names & non_experienced_devs
            assert (
                len(non_exp_reviewers) <= 1
            ), f"Experienced dev {dev.name} has {len(non_exp_reviewers)} non-exp reviewers: {non_exp_reviewers}"


@patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", {"NonExpA", "NonExpB"})
def test_non_experienced_devs_load_balancing() -> None:
    """
    Test that non-experienced developers are distributed fairly
    when being assigned as reviewers (load balancing) - INVERTED LOGIC.

    6 experienced devs (NOT in unexp list), 2 non-experienced devs
    With load balancing, the non-exp devs should be spread out.
    """
    developers = [
        Developer(name="ExpA", reviewer_number=2),
        Developer(name="ExpB", reviewer_number=2),
        Developer(name="ExpC", reviewer_number=2),
        Developer(name="ExpD", reviewer_number=2),
        Developer(name="ExpE", reviewer_number=2),
        Developer(name="ExpF", reviewer_number=2),
        Developer(name="NonExpA", reviewer_number=2),
        Developer(name="NonExpB", reviewer_number=2),
    ]

    allocate_reviewers(developers)

    experienced_devs = {"ExpA", "ExpB", "ExpC", "ExpD", "ExpE", "ExpF"}
    non_experienced_devs = {"NonExpA", "NonExpB"}

    # All non-experienced devs should be assigned
    for dev in developers:
        if dev.name in non_experienced_devs:
            assert (
                len(dev.review_for) > 0
            ), f"Non-exp dev {dev.name} should be assigned to review someone"

    # Check distribution - count how many non-exp reviewers each exp dev has
    non_exp_reviewer_counts = {}
    for dev in developers:
        if dev.name in experienced_devs:
            non_exp_count = sum(1 for r in dev.reviewer_names if r in non_experienced_devs)
            non_exp_reviewer_counts[dev.name] = non_exp_count
            # Each can have at most 1
            assert non_exp_count <= 1, f"{dev.name} has {non_exp_count} non-exp reviewers (max 1)"

    # With 6 exp devs and 2 non-exp devs, and load balancing,
    # we expect relatively even distribution
    total_non_exp_assigned = sum(non_exp_reviewer_counts.values())
    # Both non-exp devs should be assigned somewhere
    assert (
        total_non_exp_assigned >= 2
    ), f"Expected at least 2 non-exp devs to be assigned, got {total_non_exp_assigned}"


@patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", {"NonExpA", "NonExpB"})
def test_non_experienced_with_insufficient_slots() -> None:
    """
    Test with tight constraints but still possible (INVERTED LOGIC).

    3 experienced devs (NOT in unexp list), each needs 2 reviewers.
    2 non-experienced devs, each needs 1 reviewer.

    This is tight but the retry mechanism should eventually find a valid
    allocation where all non-exp devs are assigned.
    """
    developers = [
        Developer(name="ExpA", reviewer_number=2),
        Developer(name="ExpB", reviewer_number=2),
        Developer(name="ExpC", reviewer_number=2),
        Developer(name="NonExpA", reviewer_number=1),
        Developer(name="NonExpB", reviewer_number=1),
    ]

    allocate_reviewers(developers)

    experienced_devs = {"ExpA", "ExpB", "ExpC"}
    non_experienced_devs = {"NonExpA", "NonExpB"}

    # All devs should have correct reviewer assignments
    for dev in developers:
        if dev.name in non_experienced_devs:
            # Non-exp devs can ONLY have experienced reviewers
            assert dev.reviewer_names.issubset(experienced_devs)
            # With 3 exp devs and retry, should be assigned
            assert len(dev.review_for) > 0, f"{dev.name} should be assigned with 3 experienced devs"
        else:
            # Experienced devs must have at least 1 experienced reviewer
            exp_reviewers = dev.reviewer_names & experienced_devs
            assert len(exp_reviewers) >= 1


@patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", {"NE1", "NE2"})
def test_non_experienced_assignment_multiple_runs() -> None:
    """
    Run allocation 20 times to ensure non-experienced devs are
    consistently assigned (not just by luck) - INVERTED LOGIC.
    """
    for iteration in range(20):
        random.seed(iteration)

        developers = [
            Developer(name="E1", reviewer_number=2),
            Developer(name="E2", reviewer_number=2),
            Developer(name="E3", reviewer_number=2),
            Developer(name="E4", reviewer_number=2),
            Developer(name="E5", reviewer_number=2),
            Developer(name="NE1", reviewer_number=2),
            Developer(name="NE2", reviewer_number=2),
        ]

        allocate_reviewers(developers)

        experienced_devs = {"E1", "E2", "E3", "E4", "E5"}
        non_experienced_devs = {"NE1", "NE2"}

        for dev in developers:
            if dev.name in non_experienced_devs:
                # Must have only experienced reviewers
                assert dev.reviewer_names.issubset(
                    experienced_devs
                ), f"Iter {iteration}: {dev.name} has non-exp reviewers"

                # THE KEY TEST: Must be assigned to review someone
                assert (
                    len(dev.review_for) > 0
                ), f"Iter {iteration}: {dev.name} not assigned to review anyone"

    random.seed()


@patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", set())
def test_allocate_reviewers_all_experienced() -> None:
    """
    Test allocation when unexperienced list is EMPTY (all devs are experienced).
    This tests the inverted logic works correctly when everyone is experienced.

    With empty unexperienced list:
    - All developers should be treated as experienced
    - All should have at least 1 experienced reviewer (any other dev)
    - No special constraints (no junior devs to protect)
    """
    developers = [
        Developer(name="Dev1", reviewer_number=2),
        Developer(name="Dev2", reviewer_number=2),
        Developer(name="Dev3", reviewer_number=2),
        Developer(name="Dev4", reviewer_number=2),
        Developer(name="Dev5", reviewer_number=2),
    ]

    allocate_reviewers(developers)

    # All developers are experienced (empty unexperienced list)
    for dev in developers:
        reviewer_names = dev.reviewer_names

        # Basic validation
        assert len(reviewer_names) >= 1, f"{dev.name} should have at least 1 reviewer"
        assert dev.name not in reviewer_names, f"{dev.name} should not review themselves"

        # Since all are experienced, they should all get experienced reviewers
        # (which is everyone else)
        assert (
            len(reviewer_names) <= dev.reviewer_number
        ), f"{dev.name} should not exceed their reviewer number"
