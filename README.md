# Functionality
Automated reviewer assignment system that runs via GitHub Actions. The system manages two types of rotations:
- **Individual Developer Allocation**: Developer-to-developer reviewer assignments with load balancing
- **Teams Rotation**: Team-based reviewer assignments with smart member selection

All configuration is managed through Google Sheets (uses first and second sheet tabs), and assignments are automatically updated every 15 days or can be triggered manually.

## Individual Developer Allocation
Assigns reviewers to individual developers with intelligent load balancing:
- **Random selection** with preference support for specific reviewers
- **Load balanced**: Prevents scenarios where one reviewer gets 5 assignments while others get 0
- **Experienced dev guarantee**: Every developer gets at least one experienced developer as a reviewer
- **Customizable**: Each developer can specify their own number of reviewers and preferred reviewers

## Teams Rotation
Assigns reviewers to teams based on team composition:
- **Smart selection**: Uses team members when available, fills with experienced developers when needed
- **Load balanced**: Distributes team review assignments fairly across all developers
- **Flexible**: Each team can specify its own number of reviewers
- **Automated**: Runs on the same schedule as Individual Developers allocation


# Configurable parameters

## Google Sheet Columns

### First Sheet (Individual Developers):
- **"Developer"**: Unique name of developers in the team
- **"Number of Reviewers"**: How many reviewers should be assigned for this developer
- **"Preferable Reviewers"**: Comma-separated list of preferred reviewer names (optional)
  - If specified, the system will try to assign these reviewers first
  - If more reviewers are needed, they will be picked randomly from other developers
  - Load balancing ensures fair distribution even with preferences

### Second Sheet (Teams):
- **"Team"**: Unique team name
- **"Team Developers"**: Comma-separated list of developers in this team
- **"Number of Reviewers"**: How many reviewers this team needs (uses `DEFAULT_REVIEWER_NUMBER` if empty)

## Environment Variables / GitHub Secrets

**Required Secrets:**

1. **GOOGLE_CREDENTIALS_JSON** (GitHub Actions): Full JSON content of your Google Service Account credentials file
2. **SHEET_NAME**: The name of your Google Sheet (e.g., "PVC Front End - Code Reviewers")

**For Local Development:**
- **CREDENTIAL_FILE**: Path to your Service Account JSON file (usually `credentials.json`)
- **SHEET_NAME**: Same as above

**Configuration (No longer in secrets!):**
- ✨ **Default Number of Reviewers**: Now stored in Config sheet (Cell B2)
- ✨ **Experienced Developer Names**: Now stored in Config sheet (Column A, from A2 onwards)

This means you can update configuration directly in the Google Sheet without touching GitHub Secrets! 🎉


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
   - Create **at least two tabs** (Config and Individual Developers are required to exist)
   - You can name tabs whatever you like (code uses indices):
     - **First tab (Config)** - *Must exist, content optional*:
       - Can be completely empty (system uses defaults)
       - Or add configuration (recommended):
         - A1: "Experienced Developers", B1: "Default Number of Reviewers"
         - A2+: List experienced developer names (one per row)
         - B2: Enter default number (e.g., "2")
     - **Second tab (Individual Developers)** - *Required with content*:
       - E.g., "FE Devs", "Developers", "BE Devs", etc.
       - See template structure in `example.xlsx`
     - **Third tab (Teams)** - *Optional*:
       - E.g., "Teams", "Team Rotation", "Projects", etc.
       - Only needed if you want team-based rotations
   - Share the sheet with your Service Account email

4. **Setup environment**:
   - Copy `.env_template` to `.env` (if it exists)
   - Fill in: `CREDENTIAL_FILE=credentials.json` and `SHEET_NAME=your-sheet-name`
   - Note: No need for DEFAULT_REVIEWER_NUMBER or EXPERIENCED_DEV_NAMES!

5. **Install dependencies**:
   ```bash
   poetry install
   ```

6. **Run scripts**:
   ```bash
   # For individual developer allocation (second sheet)
   poetry run python scripts/rotate_devs_reviewers.py
   
   # For teams rotation (third sheet)
   poetry run python scripts/rotate_team_reviewers.py
   ```  

## Automated Execution with GitHub Actions

### Automated Workflow (Scheduled) 🤖

**Workflow: "Run All Review Rotations"** (`.github/workflows/all-review-rotations.yml`)

This is the **only workflow with a cron schedule**. It runs both rotations sequentially:

1. **Individual Developer Allocation** (First Sheet)
   - Checks if at least 15 days have passed since the last rotation
   - Allocates reviewers randomly with experienced dev guarantee
   - **Load Balanced**: Prioritizes reviewers with fewer assignments

2. **Teams Rotation** (Second Sheet)
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
- **"Run Developers Review Rotation"** (`.github/workflows/devs-review-rotation.yml`) - Run individual developer allocation only
- **"Run Teams Review Rotation"** (`.github/workflows/teams-review-rotation.yml`) - Run teams rotation only

**Use cases:**
- Need to update only individual developers without touching teams
- Need to update only teams without touching individual developers
- Want granular control over individual rotations
- Emergency rotation needed outside the 15-day schedule

### Assignment Logic

**Assignment Logic** (for each team with N reviewers needed):
- **0 team members**: Assigns N experienced developers (load-balanced to those with fewest team assignments)
- **Fewer members than N**: Uses all team members + fills remaining slots with experienced devs (not from the team, load-balanced)
- **Enough members**: Selects N members from the team (load-balanced to those with fewest team assignments)

**Example** (Team needs 2 reviewers):
- Team with 0 members → 2 random experienced developers from the list of all developers
- Team with 1 member → that one developer of that team + 1 experienced developer not from that team
- Team with 2 members → the 2 members of that team
- Team with 3+ members → 2 random members of that team

**Example** (Team needs 3 reviewers):
- Team with 5 members → 3 random members of that team

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
   | `EXPERIENCED_DEV_NAMES` | Comma-separated list of experienced developer names | `"Dev2, Dev3, Dev4, Dev5"` |

3. **For `GOOGLE_CREDENTIALS_JSON`:**
   - Open your Google Service Account credentials JSON file
   - Copy the **entire file content** (including the outer braces)
   - Paste it as the secret value

4. **Manual Triggers:**
   
   All workflows can be triggered manually from the GitHub Actions tab:
   
   | Workflow | What It Does | When to Use |
   |----------|-------------|-------------|
   | **Run All Review Rotations** | Runs both individual developers + teams | Most common - update everything |
   | **Run Developers Review Rotation** | Runs individual developers only | Need to update only individual developers |
   | **Run Teams Review Rotation** | Runs teams only | Need to update only teams |
   
   **How to trigger:**
   1. Go to **Actions** tab in your repository
   2. Select the workflow you want to run
   3. Click **"Run workflow"** dropdown
   4. Click **"Run workflow"** button
   
   ⚠️ **Note**: Manual triggers always execute immediately, regardless of the 15-day schedule

### Google Sheet Structure

Your Google Sheet should have **at least two sheet tabs**:

**First Sheet (Config)** - Configuration ✅ **Required to exist, content optional**
- **This sheet MUST exist** (to keep indices consistent across all sheets)
- **Content is optional** - can be completely empty, the system will use defaults
- **Recommended structure** (if you want to customize):
  - Header row (row 1): "Experienced Developers" in A1, "Default Number of Reviewers" in B1
  - Column A (A2+): List of experienced developer names (one per row)
  - Column B2: Default number of reviewers (e.g., "2")
- **If columns are missing or empty** → Uses defaults: `reviewer_number=1`, `experienced_devs=empty`
- **Minimum requirement**: Just create an empty sheet named "Config" (or any name)

**Second Sheet (index 1)** - Individual developers ✅ **Required**
- Example names: "Developers", "FE Devs", "BE Devs", etc.
- Column A: `Developer` - Developer name
- Column B: `Number of Reviewers` - How many reviewers this developer needs
- Column C: `Preferable Reviewers` - Comma-separated list of preferred reviewer names
- Column D+: Date columns with reviewer assignments (e.g., "08-10-2025")

**Third Sheet (index 2)** - Team-based rotation 🔵 **Optional**
- Example names: "Teams", "Team Rotation", "Projects", etc.
- Column A: `Team` - Team name
- Column B: `Team Developers` - Comma-separated list of developers in this team
- Column C: `Number of Reviewers` - How many reviewers this team needs (uses value from Config sheet if empty)
- Column D+: Date columns with reviewer assignments (e.g., "08-10-2025")
- **If you don't need team rotations, you can skip creating this sheet entirely**

**Note:** The code uses sheet indices (0 for Config, 1 for Individual Developers, 2 for Teams) instead of sheet names, so you're free to name your tabs whatever makes sense for your team!

**Graceful Failure:** If the Config sheet is empty or the Teams sheet is missing, the system will log a warning and use defaults/skip that rotation. Config and Individual Developers sheets must exist, but Teams is optional.

### How It Works

- **Scheduled Execution**: Every Wednesday at 5:00 AM Finland Time (3:00 AM UTC), the unified workflow checks both rotations
- **Date Checking**: Each script reads the most recent sprint/rotation date from its respective sheet tab
- **Independent Schedules**: Individual developers and teams rotate independently (can be on different 15-day cycles)
- **Smart Execution**: Only runs if 15+ days have passed (or if manually triggered)
- **Manual Override**: Manual triggers always execute immediately, independent of the schedule
- **Load Balancing**: Both systems track assignments and prioritize reviewers/developers with fewer assignments
- **Sheet Access**: Uses sheet indices (0 and 1) instead of names - name your sheets however you like!

### Load Balancing Details

**Individual Developers:**
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
