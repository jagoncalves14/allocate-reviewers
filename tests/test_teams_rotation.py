"""Tests for Teams rotation with load balancing"""
from unittest.mock import patch

import pytest

from scripts.rotate_team_reviewers import assign_team_reviewers, parse_team_developers
from lib.data_types import Developer

EXPERIENCED_DEVS = {"Pavel", "Joao", "Chris", "Robert", "Claudiu"}


class TestParseTeamDevelopers:
    """Test parsing team developers from comma-separated string"""

    def test_empty_string(self):
        result = parse_team_developers("")
        assert result == set()

    def test_single_developer(self):
        result = parse_team_developers("Pavel")
        assert result == {"Pavel"}

    def test_multiple_developers(self):
        result = parse_team_developers("Pavel, Joao, Chris")
        assert result == {"Pavel", "Joao", "Chris"}

    def test_with_extra_spaces(self):
        result = parse_team_developers("  Pavel  ,  Joao  ,  Chris  ")
        assert result == {"Pavel", "Joao", "Chris"}


class TestAssignTeamReviewers:
    """Test team reviewer assignment with load balancing"""

    @patch("lib.env_constants.EXPERIENCED_DEV_NAMES", EXPERIENCED_DEVS)
    def test_team_with_no_members(self):
        """Team with 0 members should get N random experienced devs"""
        teams = [
            Developer(
                name="Stock",
                reviewer_number=2,
                preferable_reviewer_names=set(),
            )
        ]

        assign_team_reviewers(teams)

        assert len(teams[0].reviewer_names) == 2
        # All reviewers should be experienced devs
        assert all(
            name in {"Pavel", "Joao", "Chris", "Robert", "Claudiu"}
            for name in teams[0].reviewer_names
        )

    @patch("lib.env_constants.EXPERIENCED_DEV_NAMES", EXPERIENCED_DEVS)
    def test_team_with_fewer_members_than_needed(self):
        """Team with 1 member needing 2 reviewers"""
        teams = [
            Developer(
                name="Finance Core",
                reviewer_number=2,
                preferable_reviewer_names={"Damian"},
            )
        ]

        assign_team_reviewers(teams)

        # Should have 2 reviewers
        assert len(teams[0].reviewer_names) == 2
        # Damian should be included (team member)
        assert "Damian" in teams[0].reviewer_names
        # Other reviewer should be experienced dev not in team
        other_reviewers = teams[0].reviewer_names - {"Damian"}
        assert len(other_reviewers) == 1
        assert all(
            name in {"Pavel", "Joao", "Chris", "Robert", "Claudiu"}
            for name in other_reviewers
        )

    @patch("lib.env_constants.EXPERIENCED_DEV_NAMES", EXPERIENCED_DEVS)
    def test_team_with_enough_members(self):
        """Team with 3 members needing 2 reviewers"""
        teams = [
            Developer(
                name="Clinical Foundation",
                reviewer_number=2,
                preferable_reviewer_names={"Robert", "Pavel", "Ximo"},
            )
        ]

        assign_team_reviewers(teams)

        # Should have exactly 2 reviewers
        assert len(teams[0].reviewer_names) == 2
        # All reviewers should be from team members
        assert all(
            name in {"Robert", "Pavel", "Ximo"}
            for name in teams[0].reviewer_names
        )

    @patch("lib.env_constants.EXPERIENCED_DEV_NAMES", EXPERIENCED_DEVS)
    def test_load_balancing_across_multiple_teams(self):
        """Load balancing should distribute assignments fairly"""
        teams = [
            Developer(
                name="Stock",
                reviewer_number=2,
                preferable_reviewer_names=set(),
            ),
            Developer(
                name="Data",
                reviewer_number=2,
                preferable_reviewer_names=set(),
            ),
            Developer(
                name="Enterprise 1",
                reviewer_number=2,
                preferable_reviewer_names=set(),
            ),
        ]

        assign_team_reviewers(teams)

        # Count assignments per developer
        assignment_count = {}
        for team in teams:
            for reviewer in team.reviewer_names:
                assignment_count[reviewer] = assignment_count.get(reviewer, 0) + 1

        # With 3 teams × 2 reviewers = 6 total slots
        # and 5 experienced devs, distribution should be relatively balanced
        # No dev should have more than 2 assignments (6/5 = 1.2, round up)
        assert all(count <= 2 for count in assignment_count.values())

    @patch("lib.env_constants.EXPERIENCED_DEV_NAMES", EXPERIENCED_DEVS)
    def test_different_reviewer_numbers_per_team(self):
        """Each team can have different reviewer requirements"""
        teams = [
            Developer(
                name="Team A",
                reviewer_number=1,
                preferable_reviewer_names=set(),
            ),
            Developer(
                name="Team B",
                reviewer_number=3,
                preferable_reviewer_names=set(),
            ),
        ]

        assign_team_reviewers(teams)

        assert len(teams[0].reviewer_names) == 1
        assert len(teams[1].reviewer_names) == 3

