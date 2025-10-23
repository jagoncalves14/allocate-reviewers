# Functionality
Automated reviewer assignment system that runs via GitHub Actions. The system manages two types of rotations:
- **FE Devs Allocation**: Individual developer reviewer assignments with load balancing
- **Teams Rotation**: Team-based reviewer assignments with smart member selection

All configuration is managed through Google Sheets, and assignments are automatically updated every 15 days or can be triggered manually.

## FE Devs Allocation (Individual Developers)
Assigns reviewers to individual developers with intelligent load balancing:
- **Random selection** with preference support for specific reviewers
- **Load balanced**: Prevents scenarios where one reviewer gets 5 assignments while others get 0
- **Experienced dev guarantee**: Every developer gets at least one experienced developer as a reviewer
- **Customizable**: Each developer can specify their own number of reviewers and preferred reviewers

## Teams Rotation
Assigns reviewers to teams based on team composition:
- **Smart selection**: Uses team members when available, fills with experienced devs when needed
- **Load balanced**: Distributes team review assignments fairly across all developers
- **Flexible**: Each team can specify its own number of reviewers
- **Automated**: Runs on the same schedule as FE Devs allocation


# Configurable parameters

## Google Sheet Columns

### FE Devs Tab:
- **"Developer"**: Unique name of developers in the team
- **"Number of Reviewers"**: How many reviewers should be assigned for this developer
- **"Preferable Reviewers"**: Comma-separated list of preferred reviewer names (optional)
  - If specified, the system will try to assign these reviewers first
  - If more reviewers are needed, they will be picked randomly from other developers
  - Load balancing ensures fair distribution even with preferences

### Teams Tab:
- **"Team"**: Unique team name
- **"Team Developers"**: Comma-separated list of developers in this team
- **"Number of Reviewers"**: How many reviewers this team needs (uses `DEFAULT_REVIEWER_NUMBER` if empty)

## Environment Variables / GitHub Secrets

**CREDENTIAL_FILE** (Local development only): Path to the Google Service Account credentials JSON file.

**GOOGLE_CREDENTIALS_JSON** (GitHub Actions): Full JSON content of your Google Service Account credentials file.

**SHEET_NAME**: The name of the Google Sheet that contains both "FE Devs" and "Teams" tabs.

**DEFAULT_REVIEWER_NUMBER**: Default number of reviewers (used as fallback when "Number of Reviewers" column is empty).

**EXPERIENCED_DEV_NAMES**: Comma-separated list of experienced developer names (e.g., `"Joao, Pavel, Chris, Robert"`).
- Used by **both** FE Devs and Teams rotations
- FE Devs: Ensures every developer gets at least one experienced reviewer
- Teams: Used to fill reviewer slots for teams with insufficient members


# Usage guide

## Local Development

1. **Enable Google APIs** in Google Cloud Console:
   - Enable "Google Sheets API"
   - Enable "Google Drive API" (required by gspread library)
   - Create a Service Account and download the credentials JSON

2. **Setup credentials**:
   - Create a file "credentials.json" in the project root
   - Copy the Service Account credentials into this file

3. **Setup Google Sheet**:
   - Create a new Google Sheet
   - Create two tabs: "FE Devs" and "Teams"
   - Copy the template structure from `example.xlsx`
   - Share the sheet with your Service Account email

4. **Setup environment**:
   - Copy `.env_template` to `.env`
   - Fill in the required values (CREDENTIAL_FILE, SHEET_NAME, etc.)

5. **Install dependencies**:
   ```bash
   poetry install
   ```

6. **Run scripts**:
   ```bash
   # For FE Devs allocation
   poetry run python allocate_reviewers.py
   
   # For Teams rotation
   poetry run python rotate_reviewers.py
   ```  

## Automated Execution with GitHub Actions

### Automated Workflow (Scheduled) 🤖

**Workflow: "Run All Review Rotations"** (`.github/workflows/all-review-rotations.yml`)

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
- **"Run FE Devs Review Rotation"** (`.github/workflows/fe-devs-review-rotation.yml`) - Run FE Devs allocation only
- **"Run Teams Review Rotation"** (`.github/workflows/teams-review-rotation.yml`) - Run Teams rotation only

**Use cases:**
- Need to update only FE Devs without touching Teams
- Need to update only Teams without touching FE Devs
- Want granular control over individual rotations
- Emergency rotation needed outside the 15-day schedule

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
   | **Run All Review Rotations** | Runs both FE Devs + Teams | Most common - update everything |
   | **Run FE Devs Review Rotation** | Runs FE Devs only | Need to update only individual devs |
   | **Run Teams Review Rotation** | Runs Teams only | Need to update only teams |
   
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

- **Scheduled Execution**: Every Wednesday at 5:00 AM Finland Time (3:00 AM UTC), the unified workflow checks both rotations
- **Date Checking**: Each script reads the most recent sprint/rotation date from its respective Google Sheet tab
- **Independent Schedules**: FE Devs and Teams rotate independently (can be on different 15-day cycles)
- **Smart Execution**: Only runs if 15+ days have passed (or if manually triggered)
- **Manual Override**: Manual triggers always execute immediately, independent of the schedule
- **Load Balancing**: Both systems track assignments and prioritize reviewers/developers with fewer assignments

### Load Balancing Details

**FE Devs:**
- Tracks how many developers each reviewer is assigned to
- Prioritizes reviewers with fewer current assignments
- Prevents uneven distribution (e.g., one reviewer with 5 assignments, another with 0)
- Randomizes selection among equally loaded reviewers

**Teams:**
- Tracks how many teams each developer is reviewing
- Distributes team assignments fairly across all available developers
- Works across all three assignment scenarios (no members, few members, enough members)
- Ensures workload equity in team-based reviews

### Column Header Format & Styling

The system maintains the sprint schedule even when manual runs occur:

**Scheduled runs:** Create a new column with header format `DD-MM-YYYY`
- Example: `22-10-2025`
- Header: Light blue background with black text
- Manual run column width: 280px (wider for the extra date info)

**Manual runs:** Update the existing column and modify the header to show when manual intervention happened
- First manual run: `22-10-2025 / Manual Run on: 23-10-2025`
- Subsequent manual runs: `22-10-2025 / Manual Run on: 24-10-2025`
- The original sprint date is always preserved

**Column Styling:**
- **Current sprint column** (most recent): Light blue header background, black text
- **5 previous sprint columns**: White background, light grey text (0.8 opacity)
- Older columns remain unchanged

The sprint date is always preserved, ensuring scheduled rotations remain on the 15-day cycle regardless of manual interventions.
