import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

DRIVE_SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]
SHEET_NAME = os.environ.get("SHEET_NAME")
EXPECTED_HEADERS = ["Developer", "Reviewer Number"]

DEFAULT_REVIEWER_NUMBER = int(os.environ.get("DEFAULT_REVIEWER_NUMBER") or "1")
EXPERIENCED_DEV_NAMES = set(os.environ.get("EXPERIENCED_DEV_NAMES", "").split(", "))
REVIEWERS_CONFIG_LIST = list(os.environ.get("REVIEWERS_CONFIG_LIST", "").split(", "))
