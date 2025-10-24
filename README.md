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

## Environment Variables / GitHub Configuration

### 🔒 Required Secrets (Sensitive Data)

**GitHub Actions → Settings → Secrets and variables → Actions → Secrets:**

1. **GOOGLE_CREDENTIALS_JSON**: Full JSON content of your Google Service Account credentials file
   - This is **sensitive** and should be kept secret!

### 📋 Required Variables (Non-Sensitive Config)

**GitHub Actions → Settings → Secrets and variables → Actions → Variables:**

- **SHEET_NAMES**: Sheet name(s) - one per line
  - **Single sheet:**
    ```
    Front End - Code Reviewers
    ```
  - **Multiple sheets:**
    ```
    Front End - Code Reviewers
    Backend - Code Reviewers
    Mobile - Code Reviewers
    ```
  - Works for both single and multiple sheets!
  - Each sheet must be shared with the Service Account

**Why Variables instead of Secrets?**
- ✅ **Visible**: You can see the current value
- ✅ **Editable**: Easy to update without re-entering everything
- ✅ **Same security**: Only repo admins/collaborators can access
- ✅ **Not sensitive**: Sheet names don't grant access (the Service Account credentials do)

### 🖥️ For Local Development

- **CREDENTIAL_FILE**: Path to your Service Account JSON file (usually `credentials.json`)
- **SHEET_NAMES**: Sheet name(s) - one per line

### ⚙️ Configuration (No longer in secrets!)

- ✨ **Default Number of Reviewers**: Now stored in Config sheet (Cell B2)
- ✨ **Experienced Developer Names**: Now stored in Config sheet (Column A, from A2 onwards)

This means you can update configuration directly in the Google Sheet without touching GitHub! 🎉


# Usage guide

## Local Development

### Step 1: Create Google Cloud Project & Get Credentials

1. **Go to Google Cloud Console**: https://console.cloud.google.com

2. **Create a new project** (or select existing):
   - Click the project dropdown at the top
   - Click "New Project"
   - Name it (e.g., "Code Review Rotation")
   - Click "Create"

3. **Enable required APIs**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Sheets API" → Click → Enable
   - Search for "Google Drive API" → Click → Enable

4. **Create Service Account**:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "Service Account"
   - Enter a name (e.g., "code-review-bot")
   - Click "Create and Continue"
   - Skip roles (optional) → Click "Continue"
   - Click "Done"

5. **Download Credentials JSON**:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON"
   - Click "Create" (file downloads automatically)

6. **Save credentials**:
   - Rename the downloaded file to `credentials.json`
   - Move it to your project root
   - Open the file and **find the `client_email`** - you'll need this next!
   - Example: `"client_email": "code-review-bot@your-project.iam.gserviceaccount.com"`

### Step 2: Create Google Sheet from Template

1. **Open the template**:
   - Download `example.xlsx` from this repository
   - Go to Google Sheets: https://sheets.google.com
   - Click "File" → "Import" → Upload `example.xlsx`
   - Or create a new sheet and manually create the structure

2. **Create the required tabs**:
   
   **Tab 1: Config** (Required to exist, content optional)
   ```
   A1: Experienced Developers    B1: Default Number of Reviewers
   A2: Dev2                       B2: 2
   A3: Dev3
   A4: Dev4
   ...
   ```
   
   **Tab 2: Individual Developers** (Required with content)
   ```
   A1: Developer    B1: Number of Reviewers    C1: Preferable Reviewers
   A2: Dev1         B2: 2                      C2: Dev2, Dev3
   A3: Dev2         B3: 2                      C3: Dev3, Dev4
   ...
   ```
   
   **Tab 3: Teams** (Optional)
   ```
   A1: Team         B1: Team Developers        C1: Number of Reviewers
   A2: Team1        B2: Dev1, Dev2, Dev3       C2: 2
   A3: Team2        B3: Dev4, Dev5             C3: 2
   ...
   ```

3. **Share the sheet with the Service Account**:
   - Click the "Share" button (top right)
   - Paste the **`client_email`** from your `credentials.json`
   - Example: `code-review-bot@your-project.iam.gserviceaccount.com`
   - Set permission to **Editor**
   - **Uncheck** "Notify people" (it's a bot, not a person!)
   - Click "Share"

### Step 3: Setup Environment

1. **Create environment file**:
   ```bash
   # Create .env file
   touch .env
   ```

2. **Add configuration**:
   ```bash
   # .env file contents
   CREDENTIAL_FILE=credentials.json
   SHEET_NAMES=Your Sheet Name Here
   ```
   
   **For multiple sheets:**
   ```bash
   SHEET_NAMES=PVC Front End - Code Reviewers
   PVC Backend - Code Reviewers
   PVC Mobile - Code Reviewers
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   ```

### Step 4: Run the Scripts
   
   **Single Sheet Mode:**
   ```bash
   # For individual developer allocation (second sheet)
   poetry run python scripts/rotate_devs_reviewers.py
   
   # For teams rotation (third sheet)
   poetry run python scripts/rotate_team_reviewers.py
   ```
   
   **Multi-Sheet Mode:** 🆕
   ```bash
   # Process all sheets (developers + teams)
   poetry run python scripts/run_multi_sheet_rotation.py --type all
   
   # Process only developers across all sheets
   poetry run python scripts/run_multi_sheet_rotation.py --type devs
   
   # Process only teams across all sheets
   poetry run python scripts/run_multi_sheet_rotation.py --type teams
   
   # Manual run (updates existing column instead of creating new)
   poetry run python scripts/run_multi_sheet_rotation.py --type all --manual
   ```

## Automated Execution with GitHub Actions

### 🆕 Multi-Sheet Workflow (Recommended)

**Workflow: "Multi-Sheet Review Rotation"** (`.github/workflows/multi-sheet-rotation.yml`)

This workflow processes **multiple Google Sheets** automatically:

- **Scheduled**: Runs every Wednesday at 5:00 AM Finland Time (3:00 AM UTC)
- **Manual Trigger**: Run on-demand via GitHub Actions UI
- **Configuration**: Add sheet names to `SHEET_NAMES` variable (one per line)
- **Smart**: Processes all configured sheets in sequence
- **Flexible**: Choose rotation type (all/devs/teams) and mode (scheduled/manual)

**Benefits:**
- ✅ **Multi-Team Support**: Manage rotations for Frontend, Backend, Mobile, etc.
- ✅ **Centralized**: One workflow for all teams
- ✅ **No Code Changes**: Add/remove sheets via GitHub Variables
- ✅ **Error Handling**: Continues even if one sheet fails

### Single-Sheet Workflows (Backward Compatible)

For single-sheet setups, these workflows are still available:

**Workflow: "Single Sheet - Developers Rotation"** (`.github/workflows/single-sheet-devs-rotation.yml`)
**Workflow: "Single Sheet - Teams Rotation"** (`.github/workflows/single-sheet-teams-rotation.yml`)

These workflows work with the `SHEET_NAME` variable and run:

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

2. **Add Secrets (Sensitive Data):**
   
   Click **"Secrets" tab** → "New repository secret"
   
   | Secret Name | Description | Example |
   |-------------|-------------|---------|
   | `GOOGLE_CREDENTIALS_JSON` | Full JSON content of your Google Service Account credentials file | `{"type": "service_account", ...}` |
   
   **For `GOOGLE_CREDENTIALS_JSON`:**
   - Open your Google Service Account credentials JSON file
   - Copy the **entire file content** (including the outer braces)
   - Paste it as the secret value

3. **Add Variables (Non-Sensitive Config):** 🆕
   
   Click **"Variables" tab** → "New repository variable"
   
   **Choose ONE option:**
   
   | Variable Name | Description | Example |
   |---------------|-------------|---------|
   | `SHEET_NAMES` | Sheet name(s) - one per line | See below |
   
   **Enter sheet names (one per line):**
   
   For **single sheet:**
   ```
   Front End - Code Reviewers
   ```
   
   For **multiple sheets:**
   ```
   Front End - Code Reviewers
   Backend - Code Reviewers
   Mobile - Code Reviewers
   ```
   
   ✨ **No longer needed as secrets:**
   - ~~`DEFAULT_REVIEWER_NUMBER`~~ → Now in Config sheet (Cell B2)
   - ~~`EXPERIENCED_DEV_NAMES`~~ → Now in Config sheet (Column A)

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
