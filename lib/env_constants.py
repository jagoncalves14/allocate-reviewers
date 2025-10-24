import os

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
        names = [
            name.strip()
            for name in sheet_names_env.split("\n")
            if name.strip()
        ]
        return names

    return []


# Sheet indices (0-based)
CONFIG_SHEET = 0  # First sheet - Configuration
DEVS_SHEET = 1  # Second sheet - Individual developers
TEAMS_SHEET = 2  # Third sheet - Teams

# Column names for Individual Developers allocation
INDIVIDUAL_DEVELOPERS_COLUMNS = [
    "Developer",  # Column 0: Developer name
    "Number of Reviewers",  # Column 1: Number of reviewers
    "Preferable Reviewers",  # Column 2: Preferred reviewer names
]

# Column names for Teams rotation
TEAMS_COLUMNS = [
    "Team",  # Column 0: Team name (identifier)
    "Team Developers",  # Column 1: Developers in this team
    "Number of Reviewers",  # Column 2: Number of reviewers for this team
]

# Convenient access to column names by index
DEVELOPER_HEADER = INDIVIDUAL_DEVELOPERS_COLUMNS[0]
REVIEWER_NUMBER_HEADER = INDIVIDUAL_DEVELOPERS_COLUMNS[1]
PREFERABLE_REVIEWER_HEADER = INDIVIDUAL_DEVELOPERS_COLUMNS[2]

TEAM_HEADER = TEAMS_COLUMNS[0]
TEAM_DEVELOPERS_HEADER = TEAMS_COLUMNS[1]
TEAM_REVIEWER_NUMBER_HEADER = TEAMS_COLUMNS[2]

# Expected headers for each sheet type
EXPECTED_HEADERS_FOR_ALLOCATION = INDIVIDUAL_DEVELOPERS_COLUMNS
EXPECTED_HEADERS_FOR_ROTATION = TEAMS_COLUMNS

# Default values (can be overridden by config sheet)
DEFAULT_REVIEWER_NUMBER = 1  # Fallback if config sheet is missing
EXPERIENCED_DEV_NAMES = set()  # Fallback if config sheet is missing

# API Rate Limiting
# Google Sheets API allows 60 write requests per minute per user
# Each sheet operation can make multiple write requests (insert, format, etc.)
# So we define a delay that is enough to avoid rate limits. Whenever a rate
# limit is hit, we wait for the delay below and then retry the operation.
API_RATE_LIMIT_DELAY = 10  # seconds
