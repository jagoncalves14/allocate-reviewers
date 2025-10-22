# Functionality
A simple script to assign developers to review each others' code. The assignment is done randomly.
Nonetheless, it is possible to control the preferable reviewers for each specific developer.

The script will read the configuration from a Google sheet, assign reviewers for developers in the list,
and write back the result to the Google sheet. Developers can check the name of their reviewers by accessing 
the link to the Google sheet.

A developer from the team should set up a cron job to execute the script periodically to make sure the assignment is 
rotated so that all developers have a chance to read each others' code.

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

## Local Development
1. Enable "Google Sheets API" and get the credential.
2. Create a file "some_name.json" in the same directory as "allocate_reviewer.py" lives, and copy the credential data 
to the that file.
3. Create a sheet for the script to work on.
4. Copy the template in R.xlsx to the created sheet, and fill in info.
5. Copy the template in .env_template to .env, and fill in info.
6. Use poetry to spawn a virtual env 
7. Install necessary packages by "poetry install"  
8. Start allocating reviewers by "python allocate_reviewers.py"  

## Automated Execution with GitHub Actions

The script runs automatically every 15 days on Wednesdays at 9 AM UTC via GitHub Actions. The workflow checks if at least 15 days have passed since the last rotation before executing.

### Setup Instructions

1. **Go to your repository Settings**
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret"

2. **Add the following secrets:**

   | Secret Name | Description | Example |
   |-------------|-------------|---------|
   | `GOOGLE_CREDENTIALS_JSON` | Full JSON content of your Google Service Account credentials file | `{"type": "service_account", ...}` |
   | `SHEET_NAME` | Name of your Google Sheet | `"Team Reviewers"` |
   | `DEFAULT_REVIEWER_NUMBER` | Default number of reviewers per developer | `"1"` |
   | `EXPERIENCED_DEV_NAMES` | Comma-separated list of experienced developer names | `"Alice, Bob"` |

3. **For `GOOGLE_CREDENTIALS_JSON`:**
   - Open your Google Service Account credentials JSON file
   - Copy the **entire file content** (including the outer braces)
   - Paste it as the secret value

4. **Manual Trigger:**
   - Go to Actions tab in your GitHub repository
   - Select "Allocate Reviewers" workflow
   - Click "Run workflow" button
   - This will force a rotation immediately, regardless of when the last rotation occurred
   - The scheduled cron job will continue to run as normal

### How It Works

- **Scheduled Execution**: Every Wednesday at 9 AM UTC, the workflow checks if 15 days have passed since the last rotation
- **Date Checking**: The script reads the most recent sprint date from the Google Sheet header
- **Smart Execution**: Only runs if 15+ days have passed (or if manually triggered)
- **Manual Override**: Manual triggers always execute, independent of the schedule

### Column Header Format

The system maintains the sprint schedule even when manual runs occur:

- **Scheduled runs**: Create a new column with header format `DD-MM-YYYY`
  - Example: `22-10-2025`

- **Manual runs**: Update the existing column and modify the header to show when manual intervention happened
  - First manual run: `22-10-2025 / Manual Run on: 23-10-2025`
  - Subsequent manual runs: `22-10-2025 / Manual Run on: 24-10-2025`
  
The sprint date is always preserved, ensuring scheduled rotations remain on the 15-day cycle regardless of manual interventions.
