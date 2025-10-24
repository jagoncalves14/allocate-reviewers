"""
Configuration Loader

Loads configuration from the Config sheet (first sheet in Google Sheets).
This allows all configuration to be managed directly in the sheet,
eliminating the need for GitHub Secrets.
"""
from typing import Tuple, Set

from lib.utilities import get_remote_sheet, increment_api_call_count
from lib.env_constants import CONFIG_SHEET


def load_config_from_sheet(
    sheet_name: str | None = None
) -> Tuple[int, Set[str]]:
    """
    Load configuration from the Config sheet (index 0).

    Args:
        sheet_name: Optional name of the Google Sheet file to open.
            If None, uses SHEET_NAME from environment variable.

    Expected format:
    - Column A: "Experienced Developers" with names listed below
    - Column B: "Default Number of Reviewers" with number in B2

    Returns:
        Tuple of (default_reviewer_number, experienced_dev_names)
        Falls back to defaults if Config sheet is missing or invalid
    """
    try:
        with get_remote_sheet(CONFIG_SHEET, sheet_name) as sheet:
            # Get all values from the sheet
            all_values = sheet.get_all_values()
            increment_api_call_count()  # 1 API call (get_all_values)

            # If sheet is empty or has only headers, use defaults
            # (will be caught by except block and return defaults)
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

            # Read Experienced Developers from column A (row 2 onwards)
            for i in range(1, len(all_values)):  # Skip header row
                if all_values[i] and all_values[i][0]:  # If cell A has content
                    name = all_values[i][0].strip()
                    # Skip header
                    if name and name != "Experienced Developers":
                        experienced_devs.add(name)

            if not experienced_devs:
                print(
                    "Warning: No experienced developers found in Config "
                    "sheet. All developers will be treated as "
                    "non-experienced."
                )

            print(
                f"Config loaded: Default reviewers="
                f"{default_reviewer_number}, "
                f"Experienced devs={len(experienced_devs)}"
            )

            if experienced_devs:
                print(f"   Names from Config sheet: {sorted(experienced_devs)}")

            return default_reviewer_number, experienced_devs

    except Exception as e:  # noqa: BLE001
        print(
            f"Warning: Could not load Config sheet: {e}\n"
            "Using defaults: reviewer_number=1, experienced_devs=empty"
        )
        return 1, set()
