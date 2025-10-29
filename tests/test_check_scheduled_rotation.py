"""
Tests for the check_scheduled_rotation_needed.py script.
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Path to the script
SCRIPT_PATH = (
    Path(__file__).parent.parent / "scripts" / "check_scheduled_rotation_needed.py"
)


def run_check_script(last_date: str | None) -> tuple[int, str, str]:
    """
    Run the check_scheduled_rotation_needed.py script.

    Args:
        last_date: Value for LAST_SCHEDULED_ROTATION_DATE env var, or None

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    env = {}
    if last_date is not None:
        env["LAST_SCHEDULED_ROTATION_DATE"] = last_date

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        env={**subprocess.os.environ, **env},
    )

    return result.returncode, result.stdout, result.stderr


class TestCheckScheduledRotation:
    """Test suite for check_scheduled_rotation_needed.py"""

    def test_first_run_no_date_set(self):
        """Test when LAST_SCHEDULED_ROTATION_DATE is not set (first run)"""
        exit_code, stdout, stderr = run_check_script(None)

        assert exit_code == 0, "First run should return exit code 0 (rotation needed)"
        assert "No previous scheduled rotation found" in stdout
        assert "rotation is needed" in stdout
        assert "first scheduled run" in stdout

    def test_first_run_empty_date(self):
        """Test when LAST_SCHEDULED_ROTATION_DATE is empty string"""
        exit_code, stdout, stderr = run_check_script("")

        assert exit_code == 0, "Empty date should return exit code 0 (rotation needed)"
        assert "No previous scheduled rotation found" in stdout
        assert "rotation is needed" in stdout

    def test_rotation_needed_exactly_14_days(self):
        """Test when exactly 14 days have passed (rotation needed)"""
        last_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        exit_code, stdout, stderr = run_check_script(last_date)

        assert exit_code == 0, "14 days should return exit code 0 (rotation needed)"
        assert "Days since last scheduled rotation: 14" in stdout
        assert "Minimum days required: 14" in stdout
        assert "Rotation needed" in stdout
        assert "14 >= 14" in stdout

    def test_rotation_needed_more_than_14_days(self):
        """Test when more than 14 days have passed (rotation needed)"""
        last_date = (datetime.now() - timedelta(days=21)).strftime("%Y-%m-%d")
        exit_code, stdout, stderr = run_check_script(last_date)

        assert exit_code == 0, "21 days should return exit code 0 (rotation needed)"
        assert "Days since last scheduled rotation: 21" in stdout
        assert "Rotation needed" in stdout
        assert "21 >= 14" in stdout

    def test_rotation_not_needed_less_than_14_days(self):
        """Test when less than 14 days have passed (rotation not needed)"""
        last_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        exit_code, stdout, stderr = run_check_script(last_date)

        assert exit_code == 1, "7 days should return exit code 1 (rotation not needed)"
        assert "Days since last scheduled rotation: 7" in stdout
        assert "Rotation not needed yet" in stdout
        assert "7 < 14" in stdout

    def test_rotation_not_needed_13_days(self):
        """Test edge case when 13 days have passed (rotation not needed)"""
        last_date = (datetime.now() - timedelta(days=13)).strftime("%Y-%m-%d")
        exit_code, stdout, stderr = run_check_script(last_date)

        assert exit_code == 1, "13 days should return exit code 1 (rotation not needed)"
        assert "Days since last scheduled rotation: 13" in stdout
        assert "Rotation not needed yet" in stdout
        assert "13 < 14" in stdout

    def test_rotation_not_needed_same_day(self):
        """Test when rotation was today (0 days passed)"""
        last_date = datetime.now().strftime("%Y-%m-%d")
        exit_code, stdout, stderr = run_check_script(last_date)

        assert (
            exit_code == 1
        ), "Same day should return exit code 1 (rotation not needed)"
        assert "Days since last scheduled rotation: 0" in stdout
        assert "Rotation not needed yet" in stdout
        assert "0 < 14" in stdout

    def test_invalid_date_format_treated_as_first_run(self):
        """Test when date format is invalid (should treat as first run)"""
        exit_code, stdout, stderr = run_check_script("invalid-date")

        assert (
            exit_code == 0
        ), "Invalid date should return exit code 0 (rotation needed)"
        assert "Invalid date format" in stdout
        assert "Expected format: YYYY-MM-DD" in stdout
        assert "Treating as first run" in stdout

    def test_invalid_date_format_dd_mm_yyyy(self):
        """Test when date format is DD-MM-YYYY instead of YYYY-MM-DD"""
        exit_code, stdout, stderr = run_check_script("29-10-2025")

        assert (
            exit_code == 0
        ), "Wrong format should return exit code 0 (rotation needed)"
        assert "Invalid date format" in stdout
        assert "29-10-2025" in stdout

    def test_output_includes_last_date(self):
        """Test that output includes the last rotation date"""
        last_date = "2025-10-15"
        exit_code, stdout, stderr = run_check_script(last_date)

        assert "Last scheduled rotation: 2025-10-15" in stdout

    def test_output_includes_minimum_days(self):
        """Test that output includes minimum days required"""
        last_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        exit_code, stdout, stderr = run_check_script(last_date)

        assert "Minimum days required: 14" in stdout

    def test_very_old_rotation(self):
        """Test when rotation is very old (many months)"""
        last_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        exit_code, stdout, stderr = run_check_script(last_date)

        assert exit_code == 0, "365 days should return exit code 0 (rotation needed)"
        assert "Days since last scheduled rotation: 365" in stdout
        assert "Rotation needed" in stdout


class TestCheckScheduledRotationIntegration:
    """Integration tests for the rotation check workflow"""

    def test_scenario_every_2_wednesdays(self):
        """Test the typical scenario: rotation every 2 Wednesdays"""
        # Scenario: Last rotation was on Oct 15, today is Oct 29 (14 days later)
        # This simulates the real-world case

        # Week 1 Wednesday: Rotation just happened (0 days ago)
        last_date = datetime.now().strftime("%Y-%m-%d")
        exit_code, stdout, _ = run_check_script(last_date)
        assert exit_code == 1, "Same day should not trigger rotation"
        assert "0 < 14" in stdout

        # Week 2 Wednesday: 7 days after rotation (skip)
        last_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        exit_code, stdout, _ = run_check_script(last_date)
        assert exit_code == 1, "7 days should skip rotation"
        assert "7 < 14" in stdout

        # Week 3 Wednesday: 14 days after rotation (run)
        last_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        exit_code, stdout, _ = run_check_script(last_date)
        assert exit_code == 0, "14 days should trigger rotation"
        assert "14 >= 14" in stdout

        # Week 4 Wednesday: 21 days after rotation (run, if it wasn't updated after week 3)
        last_date = (datetime.now() - timedelta(days=21)).strftime("%Y-%m-%d")
        exit_code, stdout, _ = run_check_script(last_date)
        assert exit_code == 0, "21 days should trigger rotation"
        assert "21 >= 14" in stdout

    def test_manual_run_doesnt_affect_schedule(self):
        """
        Test that the script only checks the variable (manual runs don't update it).
        This is conceptual - the script itself doesn't care if it was manual or scheduled.
        """
        # This test documents that the script behavior is the same regardless
        # of how it's called. The workflow is responsible for only updating
        # the variable on scheduled runs.

        last_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        exit_code_1, _, _ = run_check_script(last_date)

        # Running again with same date should give same result
        exit_code_2, _, _ = run_check_script(last_date)

        assert exit_code_1 == exit_code_2 == 1, "Script should give consistent results"

    def test_edge_case_leap_year(self):
        """Test date calculation across leap year boundary"""
        # February 28, 2024 (leap year) + 14 days = March 13, 2024
        last_date = "2024-02-28"
        # We can't control "today" but we can verify the script handles this date
        exit_code, stdout, stderr = run_check_script(last_date)

        # Should be > 14 days from 2024-02-28 to now (2025-10-29)
        assert exit_code == 0, "Old date should trigger rotation"
        assert "Rotation needed" in stdout
