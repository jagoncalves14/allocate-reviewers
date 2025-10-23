"""
Configuration Loader

Loads configuration from the Config sheet (first sheet in Google Sheets).
This allows all configuration to be managed directly in the sheet,
eliminating the need for GitHub Secrets.
"""
from typing import Tuple, Set

from lib.utilities import get_remote_sheet
from lib.env_constants import CONFIG_SHEET


def load_config_from_sheet() -> Tuple[int, Set[str]]:
    """
    Load configuration from the Config sheet (index 0).

    Expected format:
    - Column A: "Experienced Developers" with names listed below
    - Column B: "Default Number of Reviewers" with number in B2

    Returns:
        Tuple of (default_reviewer_number, experienced_dev_names)
    """
    with get_remote_sheet(CONFIG_SHEET) as sheet:
        # Get all values from the sheet
        all_values = sheet.get_all_values()

        if not all_values or len(all_values) < 2:
            raise ValueError(
                "Config sheet is empty or missing data. "
                "Expected headers in row 1 and data in rows below."
            )

        # Default values
        default_reviewer_number = 1
        experienced_devs = set()

        # Read Default Number of Reviewers from B2
        try:
            if len(all_values[1]) >= 2 and all_values[1][1]:
                default_reviewer_number = int(all_values[1][1])
        except (ValueError, IndexError):
            print(
                "Warning: Could not read Default Number of Reviewers "
                "from B2, using default: 1"
            )

        # Read Experienced Developers from column A (starting from row 2)
        for i in range(1, len(all_values)):  # Skip header row
            if all_values[i] and all_values[i][0]:  # If cell A has content
                name = all_values[i][0].strip()
                if name and name != "Experienced Developers":  # Skip header
                    experienced_devs.add(name)

        if not experienced_devs:
            print(
                "Warning: No experienced developers found in Config sheet. "
                "All developers will be treated as non-experienced."
            )

        print(f"Config loaded: Default reviewers={default_reviewer_number}, "
              f"Experienced devs={len(experienced_devs)}")

        return default_reviewer_number, experienced_devs
