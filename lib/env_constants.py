import os
from enum import Enum

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

DRIVE_SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]


def get_sheet_names() -> list[str]:
    """
    Parse sheet names from SHEET_NAMES environment variable.
    Supports single or multiple sheets separated by newlines.

    Returns:
        List of sheet names to process
    """
    sheet_names_env = os.environ.get("SHEET_NAMES", "").strip()

    if sheet_names_env:
        # Parse multiline format (works for single or multiple sheets)
        names = [name.strip() for name in sheet_names_env.split("\n") if name.strip()]
        return names

    return []


# Sheet types enum
class SheetTypes(str, Enum):
    """Sheet type identifiers"""

    CONFIG = "config"
    DEVS = "devs"
    TEAMS = "teams"


# Column names enums
class ConfigColumns(str, Enum):
    """Column names for Configuration sheet"""

    # List of unexperienced developers
    UNEXPERIENCED_DEVELOPERS = "Unexperienced Developers"
    # Default number of reviewers
    DEFAULT_REVIEWER_NUMBER = "Default Number of Reviewers"


class DevsColumns(str, Enum):
    """Column names for Individual Developers allocation"""

    DEVELOPER = "Developer"  # Developer name (identifier)
    # Number of reviewers this developer should have
    REVIEWER_COUNT = "Number of Reviewers"
    PREFERABLE_REVIEWERS = "Preferable Reviewers"  # Preferred reviewers


class TeamsColumns(str, Enum):
    """Column names for Teams rotation"""

    TEAM = "Team"  # Team name (identifier)
    TEAM_DEVELOPERS = "Team Developers"  # Developers in this team
    # Number of reviewers for this team
    REVIEWER_COUNT = "Number of Reviewers"


class SheetIndicesFallback(int, Enum):
    """
    Fallback sheet indices (0-based) for when auto-detection is not used.
    Most common layout: Config at 0, Devs at 1, Teams at 2.
    Note: run_multi_sheet_rotation.py uses auto-detection instead.
    """

    CONFIG = 0  # Configuration (default index)
    DEVS = 1  # Individual developers (default index)
    TEAMS = 2  # Teams (default index)


# Legacy column name lists (kept for backward compatibility)
INDIVIDUAL_DEVELOPERS_COLUMNS = [
    DevsColumns.DEVELOPER.value,
    DevsColumns.REVIEWER_COUNT.value,
    DevsColumns.PREFERABLE_REVIEWERS.value,
]  # noqa: E501

TEAMS_COLUMNS = [
    TeamsColumns.TEAM.value,
    TeamsColumns.TEAM_DEVELOPERS.value,
    TeamsColumns.REVIEWER_COUNT.value,
]

# Convenient access to column names (using enums)
DEVELOPER_HEADER = DevsColumns.DEVELOPER.value
REVIEWER_NUMBER_HEADER = DevsColumns.REVIEWER_COUNT.value
PREFERABLE_REVIEWER_HEADER = DevsColumns.PREFERABLE_REVIEWERS.value

TEAM_HEADER = TeamsColumns.TEAM.value
TEAM_DEVELOPERS_HEADER = TeamsColumns.TEAM_DEVELOPERS.value
TEAM_REVIEWER_NUMBER_HEADER = TeamsColumns.REVIEWER_COUNT.value

# Expected headers for each sheet type
EXPECTED_HEADERS_FOR_ALLOCATION = INDIVIDUAL_DEVELOPERS_COLUMNS
EXPECTED_HEADERS_FOR_ROTATION = TEAMS_COLUMNS

# Default values (can be overridden by config sheet)
DEFAULT_REVIEWER_NUMBER = 1  # Fallback if config sheet is missing
UNEXPERIENCED_DEV_NAMES = set[str]()  # Fallback: empty = all are experienced

# Rotation types (only devs and teams can be rotated, config is just configuration)
ROTATION_TYPES = [SheetTypes.DEVS.value, SheetTypes.TEAMS.value]

# Rotation scheduling
MINIMUM_DAYS_BETWEEN_ROTATIONS = 14  # 2 weeks (Wednesday to Wednesday)

# API Rate Limiting
# Google Sheets API allows 60 write requests per minute per user
# Each sheet operation can make multiple write requests (insert, format, etc.)
# So we define a delay that is enough to avoid rate limits. Whenever a rate
# limit is hit, we wait for the delay below and then retry the operation.
API_RATE_LIMIT_DELAY = 10  # seconds
