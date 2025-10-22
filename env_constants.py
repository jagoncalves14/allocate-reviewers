import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

DRIVE_SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]
SHEET_NAME = os.environ.get("SHEET_NAME")

# Column names for FE Devs allocation
FE_DEVS_COLUMNS = [
    "Developer",  # Column 0: Developer name
    "Number of Reviewers",  # Column 1: Number of reviewers
    "Preferable Reviewers",  # Column 2: Preferred reviewer names
]

# Column names for Teams rotation
TEAMS_COLUMNS = [
    "Team Developers",  # Column 0: Team/Developer name
    "Number of Reviewers",  # Column 1: Number of reviewers
    "Indexes",  # Column 2: Rotation indexes
]

# Convenient access to column names by index
DEVELOPER_HEADER = FE_DEVS_COLUMNS[0]
REVIEWER_NUMBER_HEADER = FE_DEVS_COLUMNS[1]
PREFERABLE_REVIEWER_HEADER = FE_DEVS_COLUMNS[2]

TEAM_DEVELOPER_HEADER = TEAMS_COLUMNS[0]
ALLOCATION_INDEXES_HEADER = TEAMS_COLUMNS[2]

# Expected headers for each sheet type
EXPECTED_HEADERS_FOR_ALLOCATION = FE_DEVS_COLUMNS
EXPECTED_HEADERS_FOR_ROTATION = TEAMS_COLUMNS

# Environment variables
DEFAULT_REVIEWER_NUMBER = int(
    os.environ.get("DEFAULT_REVIEWER_NUMBER") or "1"
)
EXPERIENCED_DEV_NAMES = set(
    os.environ.get("EXPERIENCED_DEV_NAMES", "").split(", ")
)
REVIEWERS_CONFIG_LIST = list(
    os.environ.get("REVIEWERS_CONFIG_LIST", "").split(", ")
)
