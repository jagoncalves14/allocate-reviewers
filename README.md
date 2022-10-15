# Functionality
A simple script to assign developers to review each other code. The assignment is done randomly.
Nonetheless, it is possible to control the preferable reviewers for each specific developer.

The script will read the configuration from a Google sheet, assign reviewers for developers in the list,
and write back the result to the Google sheet. Developers can check the name of their reviewers by accessing 
the link to the Google sheet.

A developer from the team should set up a cron job to execute the script periodically to make sure the assignment is 
rotated so that all developers have a chance to read the code of each other.

# Configurable parameters

## Google sheet
"Developer": unique name of developers in the team.

"Reviewer Number": how many reviewers should be assigned for the developer.

"Preferable Reviewers": who should be the primary reviewers for the developer.
- If the number of "Preferable Reviewers" is bigger than the "Reviewer Number", reviewers will be picked randomly from 
"Preferable Reviewers".
- If the number of "Preferable Reviewers" is less than the "Reviewer Number", reviewers will be the ones in 
"Preferable Reviewers", plus the ones that be picked randomly from the rest of developers.

## Environment variables
CREDENTIAL_FILE: the name of the json file contains credential in json format. The script needs this credential to be 
able to read and write to the Google sheet. The file should be placed in the same directory as "allocate_reviewer.py" 
lives. If you do not know what "credential in json format is", you might need to read this article 
https://www.makeuseof.com/tag/read-write-google-sheets-python/ to set thing up in Google side.

SHEET_NAME: the name of Google sheet that the script will work on.

DEFAULT_REVIEWER_NUMBER: the default reviewer number.

EXPERIENCED_DEV_NAMES: if provided, each developer will always have a reviewer from one of the experienced developers. 


# Usage guide
1. Enable "Google Sheets API" and get the credential.
2. Create a file "some_name.json" in the same directory as "allocate_reviewer.py" lives, and copy the credential data 
to the that file.
3. Create a sheet for the script to work on.
4. Copy the template in R.xlsx to the created sheet, and fill in info.
5. Copy the template in .env_template to .env, and fill in info.
6. Using poetry to spawn a virtual env and execute "python allocate_reviewers.py"  
7. Optionally you can set up a cron job to do the job periodically using the template in "execute.sh"
