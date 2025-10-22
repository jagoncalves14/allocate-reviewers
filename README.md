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

### Automated Workflow (Scheduled) 🤖

**Workflow: "Run All Rotations"** (`.github/workflows/run-all-rotations.yml`)

This is the **only workflow with a cron schedule**. It runs both rotations sequentially:

1. **FE Devs Allocation** (Individual Developers)
   - Checks if at least 15 days have passed since the last rotation
   - Allocates reviewers randomly with experienced dev guarantee
   - **Load Balanced**: Prioritizes reviewers with fewer assignments

2. **Teams Rotation**
   - Checks if at least 15 days have passed since the last rotation
   - Assigns reviewers to teams based on team composition
   - Each team can specify its own "Number of Reviewers" in the sheet
   - **Load Balanced**: Tracks how many teams each developer is reviewing

**Schedule:** Every Wednesday at 5:00 AM Finland Time (3:00 AM UTC)

**Benefits:**
- ✅ **No Race Conditions**: Runs sequentially, not simultaneously
- ✅ **Independent Schedules**: Each rotation runs only if needed (15+ days)
- ✅ **Automated**: Runs without manual intervention
- ✅ **Clear Summary**: Shows which rotations ran/skipped

### Manual Workflows (On-Demand Only) 🔧

Two additional workflows are available for **manual execution only** (no cron):
- **"Allocate FE Devs Reviews"** - Run FE Devs allocation only
- **"Allocate Teams Reviewers"** - Run Teams rotation only

**Use cases:**
- Need to update only FE Devs without touching Teams
- Need to update only Teams without touching FE Devs
- Want granular control over individual rotations

### Assignment Logic

**Assignment Logic** (for each team with N reviewers needed):
- **0 team members**: Assigns N experienced developers (load-balanced to those with fewest team assignments)
- **Fewer members than N**: Uses all team members + fills remaining slots with experienced devs (not from the team, load-balanced)
- **Enough members**: Selects N members from the team (load-balanced to those with fewest team assignments)

**Example** (Team needs 2 reviewers):
- Team with 0 members → 2 random experienced devs (e.g., Joao, Pavel)
- Team with 1 member (Robert) → Robert + 1 experienced dev not from team (e.g., Joao)
- Team with 2 members (Robert, Pavel) → both members
- Team with 3+ members (Robert, Pavel, Ximo) → 2 random members (e.g., Pavel, Ximo)

**Example** (Team needs 3 reviewers):
- Team with 5 members (Robert, Pavel, Ximo, Joao, Chris) → 3 random members (e.g., Pavel, Ximo, Chris)

### Setup Instructions

1. **Go to your repository Settings**
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret"

2. **Add the following secrets:**

   | Secret Name | Description | Example |
   |-------------|-------------|---------|
   | `GOOGLE_CREDENTIALS_JSON` | Full JSON content of your Google Service Account credentials file | `{"type": "service_account", ...}` |
   | `SHEET_NAME` | Name of your Google Sheet | `"PVC Front End - Code Reviewers [Demo]"` |
   | `DEFAULT_REVIEWER_NUMBER` | Number of reviewers per developer/team | `"2"` |
   | `EXPERIENCED_DEV_NAMES` | Comma-separated list of experienced developer names | `"Joao, Pavel, Claudiu, Chris"` |

3. **For `GOOGLE_CREDENTIALS_JSON`:**
   - Open your Google Service Account credentials JSON file
   - Copy the **entire file content** (including the outer braces)
   - Paste it as the secret value

4. **Manual Triggers:**
   
   All workflows can be triggered manually from the GitHub Actions tab:
   
   | Workflow | What It Does | When to Use |
   |----------|-------------|-------------|
   | **Run All Rotations** | Runs both FE Devs + Teams | Most common - update everything |
   | **Allocate FE Devs Reviews** | Runs FE Devs only | Need to update only individual devs |
   | **Allocate Teams Reviewers** | Runs Teams only | Need to update only teams |
   
   **How to trigger:**
   1. Go to **Actions** tab in your repository
   2. Select the workflow you want to run
   3. Click **"Run workflow"** dropdown
   4. Click **"Run workflow"** button
   
   ⚠️ **Note**: Manual triggers always execute immediately, regardless of the 15-day schedule

### Google Sheet Structure

Your Google Sheet should have **two tabs**:

**Tab 1: "FE Devs"** (Individual developers)
- Column A: `Developer` - Developer name
- Column B: `Number of Reviewers` - How many reviewers this developer needs
- Column C: `Preferable Reviewers` - Comma-separated list of preferred reviewer names
- Column D+: Date columns with reviewer assignments (e.g., "08-10-2025")

**Tab 2: "Teams"** (Team-based rotation)
- Column A: `Team` - Team name
- Column B: `Team Developers` - Comma-separated list of developers in this team
- Column C: `Number of Reviewers` - How many reviewers this team needs (uses `DEFAULT_REVIEWER_NUMBER` if empty)
- Column D+: Date columns with reviewer assignments (e.g., "08-10-2025")

### How It Works

- **Scheduled Execution**: Every Wednesday at 9 AM UTC, both workflows check if 15 days have passed since their last rotation
- **Date Checking**: Each script reads the most recent sprint/rotation date from its respective Google Sheet tab
- **Independent Schedules**: FE Devs and Teams rotate independently (can be on different dates)
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
