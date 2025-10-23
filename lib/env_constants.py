import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

DRIVE_SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]
SHEET_NAME = os.environ.get("SHEET_NAME")

# Sheet indices (0-based)
DEVS_SHEET = 0  # First sheet - Individual developers
TEAMS_SHEET = 1  # Second sheet - Teams

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

# Environment variables
DEFAULT_REVIEWER_NUMBER = int(
    os.environ.get("DEFAULT_REVIEWER_NUMBER") or "1"
)
_experienced_devs_str = os.environ.get("EXPERIENCED_DEV_NAMES", "")
EXPERIENCED_DEV_NAMES = (
    set(_experienced_devs_str.split(", ")) if _experienced_devs_str else set()
)
