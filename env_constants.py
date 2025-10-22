import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

DRIVE_SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]
SHEET_NAME = os.environ.get("SHEET_NAME")

DEVELOPER_HEADER = "Developer"
REVIEWER_NUMBER_HEADER = "Reviewer Number"
PREFERABLE_REVIEWER_HEADER = "Preferable Reviewers"
ALLOCATION_INDEXES_HEADER = "Indexes"

DEFAULT_REVIEWER_NUMBER = int(os.environ.get("DEFAULT_REVIEWER_NUMBER") or "1")
EXPERIENCED_DEV_NAMES = set(os.environ.get("EXPERIENCED_DEV_NAMES", "").split(", "))

EXPECTED_HEADERS_FOR_ALLOCATION = [
    DEVELOPER_HEADER,
    REVIEWER_NUMBER_HEADER,
    PREFERABLE_REVIEWER_HEADER,
]


EXPECTED_HEADERS_FOR_ROTATION = [
    DEVELOPER_HEADER,
    REVIEWER_NUMBER_HEADER,
    ALLOCATION_INDEXES_HEADER,
]
REVIEWERS_CONFIG_LIST = list(os.environ.get("REVIEWERS_CONFIG_LIST", "").split(", "))
