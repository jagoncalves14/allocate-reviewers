"""
Tests to verify that DEFAULT_REVIEWER_NUMBER from Config sheet is properly used
when the "Number of Reviewers" column is empty for individual developers.
"""

from unittest.mock import MagicMock, patch

from lib.utilities import load_developers_from_sheet


@patch("lib.utilities.get_remote_sheet")
def test_load_developers_uses_config_default_when_column_empty(mock_get_remote_sheet):
    """
    Test that when Number of Reviewers column is empty,
    the default from Config sheet (env_constants.DEFAULT_REVIEWER_NUMBER) is used.
    """
    # Mock sheet data with empty Number of Reviewers
    mock_sheet = MagicMock()
    mock_sheet.get_all_records.return_value = [
        {
            "Developer": "Alex",
            "Number of Reviewers": "",  # Empty - should use default
            "Preferable Reviewers": "",
        },
        {
            "Developer": "Grigorii",
            "Number of Reviewers": "",  # Empty - should use default
            "Preferable Reviewers": "",
        },
        {
            "Developer": "Imad",
            "Number of Reviewers": "3",  # Explicit value - should use this
            "Preferable Reviewers": "",
        },
    ]
    mock_get_remote_sheet.return_value.__enter__.return_value = mock_sheet

    # Set the config default to 2
    from lib import env_constants

    original_default = env_constants.DEFAULT_REVIEWER_NUMBER
    env_constants.DEFAULT_REVIEWER_NUMBER = 2

    try:
        # Load developers
        developers = load_developers_from_sheet(
            expected_headers=["Developer", "Number of Reviewers", "Preferable Reviewers"]
        )

        # Verify results
        assert len(developers) == 3

        alex = next(d for d in developers if d.name == "Alex")
        grigorii = next(d for d in developers if d.name == "Grigorii")
        imad = next(d for d in developers if d.name == "Imad")

        # Alex and Grigorii should have the default value (2)
        assert (
            alex.reviewer_number == 2
        ), f"Alex should have default reviewer_number=2, got {alex.reviewer_number}"
        assert (
            grigorii.reviewer_number == 2
        ), f"Grigorii should have default reviewer_number=2, got {grigorii.reviewer_number}"

        # Imad should have the explicit value (3)
        assert (
            imad.reviewer_number == 3
        ), f"Imad should have explicit reviewer_number=3, got {imad.reviewer_number}"

    finally:
        # Restore original default
        env_constants.DEFAULT_REVIEWER_NUMBER = original_default


@patch("lib.utilities.get_remote_sheet")
def test_load_developers_respects_different_config_defaults(mock_get_remote_sheet):
    """
    Test that changing the Config default affects empty columns correctly.
    This simulates different Config sheet values (e.g., default=1 vs default=3).
    """
    mock_sheet = MagicMock()
    mock_sheet.get_all_records.return_value = [
        {
            "Developer": "Dev1",
            "Number of Reviewers": "",  # Empty - should use default
            "Preferable Reviewers": "",
        },
    ]
    mock_get_remote_sheet.return_value.__enter__.return_value = mock_sheet

    from lib import env_constants

    original_default = env_constants.DEFAULT_REVIEWER_NUMBER

    try:
        # Test with default = 1
        env_constants.DEFAULT_REVIEWER_NUMBER = 1
        developers = load_developers_from_sheet(
            expected_headers=["Developer", "Number of Reviewers", "Preferable Reviewers"]
        )
        assert (
            developers[0].reviewer_number == 1
        ), "Should use default=1 when Number of Reviewers is empty"

        # Test with default = 3
        env_constants.DEFAULT_REVIEWER_NUMBER = 3
        developers = load_developers_from_sheet(
            expected_headers=["Developer", "Number of Reviewers", "Preferable Reviewers"]
        )
        assert (
            developers[0].reviewer_number == 3
        ), "Should use default=3 when Number of Reviewers is empty"

        # Test with default = 5
        env_constants.DEFAULT_REVIEWER_NUMBER = 5
        developers = load_developers_from_sheet(
            expected_headers=["Developer", "Number of Reviewers", "Preferable Reviewers"]
        )
        assert (
            developers[0].reviewer_number == 5
        ), "Should use default=5 when Number of Reviewers is empty"

    finally:
        env_constants.DEFAULT_REVIEWER_NUMBER = original_default


@patch("lib.utilities.get_remote_sheet")
def test_explicit_zero_is_respected(mock_get_remote_sheet):
    """
    Test that an explicit 0 in the Number of Reviewers column is respected
    (not treated as empty).
    """
    mock_sheet = MagicMock()
    mock_sheet.get_all_records.return_value = [
        {
            "Developer": "Dev1",
            "Number of Reviewers": "0",  # Explicit 0
            "Preferable Reviewers": "",
        },
    ]
    mock_get_remote_sheet.return_value.__enter__.return_value = mock_sheet

    from lib import env_constants

    original_default = env_constants.DEFAULT_REVIEWER_NUMBER
    env_constants.DEFAULT_REVIEWER_NUMBER = 2

    try:
        developers = load_developers_from_sheet(
            expected_headers=["Developer", "Number of Reviewers", "Preferable Reviewers"]
        )

        # Explicit 0 should be used, not the default
        assert (
            developers[0].reviewer_number == 0
        ), "Explicit 0 should be respected, not replaced with default"

    finally:
        env_constants.DEFAULT_REVIEWER_NUMBER = original_default
