"""Tests for Teams rotation with load balancing"""

from unittest.mock import patch

from lib.data_types import Developer
from scripts.rotate_team_reviewers import assign_team_reviewers, parse_team_developers

# INVERTED LOGIC: List unexperienced devs, everyone else is experienced
UNEXPERIENCED_DEVS = {"Dev1", "Dev7", "Dev8", "Dev9", "Dev10", "Dev11", "Dev12"}


class TestParseTeamDevelopers:
    """Test parsing team developers from comma-separated string"""

    def test_empty_string(self):
        result = parse_team_developers("")
        assert result == set()

    def test_single_developer(self):
        result = parse_team_developers("Dev2")
        assert result == {"Dev2"}

    def test_multiple_developers(self):
        result = parse_team_developers("Dev2, Dev3, Dev4")
        assert result == {"Dev2", "Dev3", "Dev4"}

    def test_with_extra_spaces(self):
        result = parse_team_developers("  Dev2  ,  Dev3  ,  Dev4  ")
        assert result == {"Dev2", "Dev3", "Dev4"}


class TestAssignTeamReviewers:
    """Test team reviewer assignment with load balancing"""

    @patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", UNEXPERIENCED_DEVS)
    def test_team_with_no_members(self):
        """Team with 0 members should get N random experienced devs"""
        teams = [
            Developer(
                name="Team8",
                reviewer_number=2,
                preferable_reviewer_names=set(),
            )
        ]

        # Provide all developers so experienced devs can be determined
        all_devs = ["Dev2", "Dev3", "Dev4", "Dev5", "Dev6", "Dev7"]
        assign_team_reviewers(teams, all_developers=all_devs)

        assert len(teams[0].reviewer_names) == 2
        # All reviewers should be experienced devs (not in UNEXPERIENCED_DEVS)
        assert all(
            name in {"Dev2", "Dev3", "Dev4", "Dev5", "Dev6"} for name in teams[0].reviewer_names
        )

    @patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", UNEXPERIENCED_DEVS)
    def test_team_with_fewer_members_than_needed(self):
        """Team with 1 member needing 2 reviewers"""
        teams = [
            Developer(
                name="Team2",
                reviewer_number=2,
                preferable_reviewer_names={"Dev7"},
            )
        ]

        # Provide all developers so experienced devs can be determined
        all_devs = ["Dev2", "Dev3", "Dev4", "Dev5", "Dev6", "Dev7"]
        assign_team_reviewers(teams, all_developers=all_devs)

        # Should have 2 reviewers
        assert len(teams[0].reviewer_names) == 2
        # Dev7 should be included (team member)
        assert "Dev7" in teams[0].reviewer_names
        # Other reviewer should be experienced dev not in team
        other_reviewers = teams[0].reviewer_names - {"Dev7"}
        assert len(other_reviewers) == 1
        assert all(name in {"Dev2", "Dev3", "Dev4", "Dev5", "Dev6"} for name in other_reviewers)

    @patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", UNEXPERIENCED_DEVS)
    def test_team_with_enough_members(self):
        """Team with 3 members needing 2 reviewers"""
        teams = [
            Developer(
                name="Team1",
                reviewer_number=2,
                preferable_reviewer_names={"Dev5", "Dev2", "Dev10"},
            )
        ]

        assign_team_reviewers(teams)

        # Should have exactly 2 reviewers
        assert len(teams[0].reviewer_names) == 2
        # All reviewers should be from team members
        assert all(name in {"Dev5", "Dev2", "Dev10"} for name in teams[0].reviewer_names)

    @patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", UNEXPERIENCED_DEVS)
    def test_load_balancing_across_multiple_teams(self):
        """Load balancing should distribute assignments fairly"""
        teams = [
            Developer(
                name="Team3",
                reviewer_number=2,
                preferable_reviewer_names=set(),
            ),
            Developer(
                name="Team4",
                reviewer_number=2,
                preferable_reviewer_names=set(),
            ),
            Developer(
                name="Team5",
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

    @patch("lib.env_constants.UNEXPERIENCED_DEV_NAMES", UNEXPERIENCED_DEVS)
    def test_different_reviewer_numbers_per_team(self):
        """Each team can have different reviewer requirements"""
        teams = [
            Developer(
                name="Team6",
                reviewer_number=1,
                preferable_reviewer_names=set(),
            ),
            Developer(
                name="Team7",
                reviewer_number=3,
                preferable_reviewer_names=set(),
            ),
        ]

        # Provide all developers so experienced devs can be determined
        all_devs = ["Dev2", "Dev3", "Dev4", "Dev5", "Dev6"]
        assign_team_reviewers(teams, all_developers=all_devs)

        assert len(teams[0].reviewer_names) == 1
        assert len(teams[1].reviewer_names) == 3
