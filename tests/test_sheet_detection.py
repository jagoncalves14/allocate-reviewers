"""
Tests for sheet type detection functionality.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the functions we're testing
from lib.env_constants import SheetTypes  # noqa: E402
from scripts.run_multi_sheet_rotation import detect_all_sheet_types, detect_sheet_type  # noqa: E402


class TestDetectSheetType:
    """Tests for detect_sheet_type function"""

    @patch("scripts.run_multi_sheet_rotation.get_remote_sheet")
    def test_detect_devs_sheet(self, mock_get_remote_sheet):
        """Test detection of Developer sheet"""

        # Mock worksheet with "Developer" as first column
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = [
            "Developer",
            "Reviewer Count",
            "Exclude From Reviewers",
            "Some Column",
        ]
        mock_get_remote_sheet.return_value.__enter__.return_value = mock_worksheet

        result = detect_sheet_type("Test Sheet", 1)

        assert result == SheetTypes.DEVS
        mock_get_remote_sheet.assert_called_once_with(1, sheet_name="Test Sheet")
        mock_worksheet.row_values.assert_called_once_with(1)

    @patch("scripts.run_multi_sheet_rotation.get_remote_sheet")
    def test_detect_config_sheet(self, mock_get_remote_sheet):
        """Test detection of Config sheet"""

        # Mock worksheet with "Unexperienced Developers" as first column
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = [
            "Unexperienced Developers",
            "Default Number of Reviewers",
        ]
        mock_get_remote_sheet.return_value.__enter__.return_value = mock_worksheet

        result = detect_sheet_type("Test Sheet", 0)

        assert result == SheetTypes.CONFIG
        mock_get_remote_sheet.assert_called_once_with(0, sheet_name="Test Sheet")

    @patch("scripts.run_multi_sheet_rotation.get_remote_sheet")
    def test_detect_teams_sheet(self, mock_get_remote_sheet):
        """Test detection of Team sheet"""

        # Mock worksheet with "Team" as first column
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = [
            "Team",
            "Reviewer Count",
            "Team Members",
        ]
        mock_get_remote_sheet.return_value.__enter__.return_value = mock_worksheet

        result = detect_sheet_type("Test Sheet", 2)

        assert result == SheetTypes.TEAMS
        mock_get_remote_sheet.assert_called_once_with(2, sheet_name="Test Sheet")

    @patch("scripts.run_multi_sheet_rotation.get_remote_sheet")
    def test_detect_unknown_sheet_type(self, mock_get_remote_sheet):
        """Test detection returns None for unknown sheet type"""

        # Mock worksheet with unrecognized first column
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = ["Unknown Column", "Other Data"]
        mock_get_remote_sheet.return_value.__enter__.return_value = mock_worksheet

        result = detect_sheet_type("Test Sheet", 3)

        assert result is None

    @patch("scripts.run_multi_sheet_rotation.get_remote_sheet")
    def test_detect_empty_sheet(self, mock_get_remote_sheet):
        """Test detection returns None for empty sheet"""

        # Mock worksheet with no data
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = []
        mock_get_remote_sheet.return_value.__enter__.return_value = mock_worksheet

        result = detect_sheet_type("Test Sheet", 0)

        assert result is None

    @patch("scripts.run_multi_sheet_rotation.get_remote_sheet")
    def test_detect_sheet_doesnt_exist(self, mock_get_remote_sheet):
        """Test detection returns None when sheet doesn't exist"""

        # Mock worksheet raising exception
        mock_get_remote_sheet.side_effect = Exception("Worksheet not found")

        result = detect_sheet_type("Test Sheet", 10)

        assert result is None

    @patch("scripts.run_multi_sheet_rotation.get_remote_sheet")
    def test_detect_with_whitespace(self, mock_get_remote_sheet):
        """Test detection handles whitespace in column names"""

        # Mock worksheet with whitespace around column name
        mock_worksheet = MagicMock()
        mock_worksheet.row_values.return_value = ["  Developer  ", "Other"]
        mock_get_remote_sheet.return_value.__enter__.return_value = mock_worksheet

        result = detect_sheet_type("Test Sheet", 1)

        assert result == SheetTypes.DEVS


class TestDetectAllSheetTypes:
    """Tests for detect_all_sheet_types function"""

    @patch("scripts.run_multi_sheet_rotation.detect_sheet_type")
    def test_detect_all_common_case(self, mock_detect):
        """Test detection of common sheet layout: Config, Devs, Teams"""

        # Mock detection results for each index
        def detect_side_effect(sheet_name, index):
            if index == 0:
                return SheetTypes.CONFIG
            elif index == 1:
                return SheetTypes.DEVS
            elif index == 2:
                return SheetTypes.TEAMS
            else:
                return None

        mock_detect.side_effect = detect_side_effect

        result = detect_all_sheet_types("Test Sheet")

        assert result == {SheetTypes.CONFIG: 0, SheetTypes.DEVS: 1, SheetTypes.TEAMS: 2}
        assert mock_detect.call_count == 5  # Checks up to 5 sheets

    @patch("scripts.run_multi_sheet_rotation.detect_sheet_type")
    def test_detect_only_devs(self, mock_detect):
        """Test detection when only Devs sheet exists"""

        # Mock detection: only devs at index 0
        def detect_side_effect(_sheet_name, index):
            return SheetTypes.DEVS if index == 0 else None

        mock_detect.side_effect = detect_side_effect

        result = detect_all_sheet_types("Test Sheet")

        assert result == {SheetTypes.DEVS: 0}

    @patch("scripts.run_multi_sheet_rotation.detect_sheet_type")
    def test_detect_only_teams(self, mock_detect):
        """Test detection when only Teams sheet exists"""

        # Mock detection: only teams at index 1
        def detect_side_effect(_sheet_name, index):
            return SheetTypes.TEAMS if index == 1 else None

        mock_detect.side_effect = detect_side_effect

        result = detect_all_sheet_types("Test Sheet")

        assert result == {SheetTypes.TEAMS: 1}

    @patch("scripts.run_multi_sheet_rotation.detect_sheet_type")
    def test_detect_custom_order(self, mock_detect):
        """Test detection with non-standard sheet order"""

        # Mock detection: unusual order (Teams, Devs, Config)
        def detect_side_effect(_sheet_name, index):
            if index == 0:
                return SheetTypes.TEAMS
            elif index == 1:
                return SheetTypes.DEVS
            elif index == 2:
                return SheetTypes.CONFIG
            else:
                return None

        mock_detect.side_effect = detect_side_effect

        result = detect_all_sheet_types("Test Sheet")

        assert result == {SheetTypes.TEAMS: 0, SheetTypes.DEVS: 1, SheetTypes.CONFIG: 2}

    @patch("scripts.run_multi_sheet_rotation.detect_sheet_type")
    def test_detect_no_sheets(self, mock_detect):
        """Test detection when no recognized sheets exist"""

        # Mock detection: no recognized sheets
        mock_detect.return_value = None

        result = detect_all_sheet_types("Test Sheet")

        assert result == {}

    @patch("scripts.run_multi_sheet_rotation.detect_sheet_type")
    def test_detect_devs_and_config_only(self, mock_detect):
        """Test detection with Devs and Config but no Teams"""

        # Mock detection: config and devs, no teams
        def detect_side_effect(_sheet_name, index):
            if index == 0:
                return SheetTypes.CONFIG
            elif index == 1:
                return SheetTypes.DEVS
            else:
                return None

        mock_detect.side_effect = detect_side_effect

        result = detect_all_sheet_types("Test Sheet")

        assert result == {SheetTypes.CONFIG: 0, SheetTypes.DEVS: 1}
        assert SheetTypes.TEAMS not in result

    @patch("scripts.run_multi_sheet_rotation.detect_sheet_type")
    @patch("builtins.print")
    def test_detect_prints_found_sheets(self, mock_print, mock_detect):
        """Test that detection prints information about found sheets"""

        # Mock detection: config, devs, teams
        def detect_side_effect(_sheet_name, index):
            if index == 0:
                return SheetTypes.CONFIG
            elif index == 1:
                return SheetTypes.DEVS
            elif index == 2:
                return SheetTypes.TEAMS
            else:
                return None

        mock_detect.side_effect = detect_side_effect

        detect_all_sheet_types("Test Sheet")

        # Verify print was called for each found sheet
        assert mock_print.call_count == 3

        # Check that appropriate messages were printed
        print_args = [call[0][0] for call in mock_print.call_args_list]
        assert any("CONFIG" in arg for arg in print_args)
        assert any("DEVS" in arg for arg in print_args)
        assert any("TEAMS" in arg for arg in print_args)


class TestSheetDetectionIntegration:
    """Integration tests for sheet detection"""

    @patch("scripts.run_multi_sheet_rotation.get_remote_sheet")
    def test_full_detection_workflow(self, mock_get_remote_sheet):
        """Test complete detection workflow with all sheet types"""

        # Create mock worksheets for each type
        def get_remote_sheet_side_effect(index, sheet_name=None):
            mock_context = MagicMock()
            mock_ws = MagicMock()
            if index == 0:
                mock_ws.row_values.return_value = [
                    "Unexperienced Developers",
                    "Default Number of Reviewers",
                ]
            elif index == 1:
                mock_ws.row_values.return_value = ["Developer", "Reviewer Count"]
            elif index == 2:
                mock_ws.row_values.return_value = [
                    "Team",
                    "Reviewer Count",
                    "Team Members",
                ]
            else:
                raise Exception("Worksheet not found")
            mock_context.__enter__.return_value = mock_ws
            mock_context.__exit__.return_value = None
            return mock_context

        mock_get_remote_sheet.side_effect = get_remote_sheet_side_effect

        result = detect_all_sheet_types("Test Sheet")

        assert result == {SheetTypes.CONFIG: 0, SheetTypes.DEVS: 1, SheetTypes.TEAMS: 2}
        assert len(result) == 3

    @patch("scripts.run_multi_sheet_rotation.get_remote_sheet")
    def test_partial_sheet_detection(self, mock_get_remote_sheet):
        """Test detection with only some sheets present"""

        def get_remote_sheet_side_effect(index, sheet_name=None):
            mock_context = MagicMock()
            mock_ws = MagicMock()
            if index == 1:
                mock_ws.row_values.return_value = ["Developer", "Reviewer Count"]
            else:
                raise Exception("Worksheet not found")
            mock_context.__enter__.return_value = mock_ws
            mock_context.__exit__.return_value = None
            return mock_context

        mock_get_remote_sheet.side_effect = get_remote_sheet_side_effect

        result = detect_all_sheet_types("Test Sheet")

        assert result == {SheetTypes.DEVS: 1}
        assert SheetTypes.CONFIG not in result
        assert SheetTypes.TEAMS not in result
