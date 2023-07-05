# Functionality
Simple scripts to assign developers to review each other's code. The scripts will read the configuration from a Google 
sheet, assign reviewers for developers in the list, and write back the result to the Google sheet. Developers can check 
the name of their reviewers by accessing the link to the Google sheet.

A developer from the team should set up a cron job to execute one of the scripts periodically.

## Reviewers allocation script
The assignment is done randomly. Nonetheless, it is possible to control the preferable reviewers for each specific 
developer.

## Reviewers rotation script
The assignment is rotated orderly so that all developers have a chance to read each other's code.


# Configurable parameters

## Google sheet
"Developer": unique name of developers in the team.

"Reviewer Number": how many reviewers should be assigned for the developer.

"Preferable Reviewers" (only used in the allocation script): who should be the primary reviewers for the developer.
- If the number of "Preferable Reviewers" is bigger than the "Reviewer Number", reviewers will be picked randomly from 
"Preferable Reviewers".
- If the number of "Preferable Reviewers" is less than the "Reviewer Number", reviewers will be the ones in 
"Preferable Reviewers", plus the ones that be picked randomly from the rest of developers.

"Indexes" (only used in the rotation script): is used to store indexes of the current allocation.

## Environment variables
CREDENTIAL_FILE: the name of the json file contains credential in json format. The script needs this credential to be 
able to read and write to the Google sheet. The file should be placed in the same directory as "allocate_reviewer.py" 
lives. If you do not know what "credential in json format is", you might need to read this article 
https://www.makeuseof.com/tag/read-write-google-sheets-python/ to set thing up in Google side.

SHEET_NAME: the name of Google sheet that the script will work on.

DEFAULT_REVIEWER_NUMBER: the default reviewer number.

EXPERIENCED_DEV_NAMES (only used in the allocation script): if provided, each developer will always have a reviewer 
from one of the experienced developers. 

REVIEWERS_CONFIG_LIST (only used in the rotation script): is used to sort the developers list before making assignment.
Recommendation: intertwine developers by their level of experience.


# Usage guide
1. Enable "Google Sheets API" and get the credential.
2. Create a file "some_name.json" in the same directory as "allocate_reviewer.py" lives, and copy the credential data 
to the that file.
3. Create a sheet for the script to work on.
4. Copy the template in R.xlsx to the created sheet, and fill in info.
5. Copy the template in .env_template to .env, and fill in info.
6. Use poetry to spawn a virtual env 
7. Install necessary packages by "poetry install"  
8. Start allocating reviewers by "python allocate_reviewers.py" or "python rotate_reviewers.py" 
9. Optionally you can set up a cron job to do the job periodically using the template in "execute.sh"


# TODO:
- Tests for the rotation script.
- Support skipping devs on vacation.
