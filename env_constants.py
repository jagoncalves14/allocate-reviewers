import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

DRIVE_SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]
SHEET_NAME = os.environ.get("SHEET_NAME")
DEFAULT_REVIEWER_NUMBER = int(os.environ.get("DEFAULT_REVIEWER_NUMBER") or "1")

EXPECTED_HEADERS_FOR_ALLOCATION = [
    "Developer",
    "Reviewer Number",
    "Preferable Reviewers",
]
EXPERIENCED_DEV_NAMES = set(os.environ.get("EXPERIENCED_DEV_NAMES", "").split(", "))

EXPECTED_HEADERS_FOR_ROTATION = ["Developer", "Reviewer Number"]
REVIEWERS_CONFIG_LIST = list(os.environ.get("REVIEWERS_CONFIG_LIST", "").split(", "))
