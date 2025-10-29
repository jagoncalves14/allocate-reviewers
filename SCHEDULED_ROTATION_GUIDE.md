# Scheduled Rotation Guide

## Overview

This project uses a **GitHub Variable** to track scheduled rotations separately from manual runs. This ensures that manual runs don't interfere with the 15-day scheduled rotation cycle.

## How It Works

### The Problem (Old Approach)
Previously, the system checked the last rotation date by parsing the column headers in the Google Sheet. This caused issues:
- ❌ Manual runs would reset the 15-day counter
- ❌ Parsing column headers was complex and error-prone
- ❌ No clear separation between scheduled and manual runs

### The Solution (New Approach)
Now we use a GitHub Variable to store the last **scheduled** rotation date:
- ✅ **GitHub Variable**: `LAST_SCHEDULED_ROTATION_DATE`
- ✅ **Format**: `YYYY-MM-DD` (e.g., `2025-10-29`)
- ✅ **Only updated by scheduled runs** (manual runs don't affect it)
- ✅ **Visible in GitHub UI** (Settings → Secrets and variables → Actions → Variables)
- ✅ **Simple and reliable**

## Setup

### 1. Create the GitHub Variable

Go to your repository:
1. **Settings** → **Secrets and variables** → **Actions** → **Variables** tab
2. Click **"New repository variable"**
3. **Name**: `LAST_SCHEDULED_ROTATION_DATE`
4. **Value**: Leave empty for first run, or set to a date in format `YYYY-MM-DD`
5. Click **"Add variable"**

### 2. Workflow Automatically Updates It

After each **successful scheduled rotation**, the workflow automatically updates this variable with today's date.

**You don't need to manually update it!**

## How the Schedule Works

**Rotation Frequency: Every 2 Wednesdays (14 days)**

### Scheduled Runs (Cron - Every Wednesday)

```yaml
schedule:
  - cron: '0 2 * * 3'  # Every Wednesday at 2 AM UTC
```

**On every Wednesday:**

1. **Check** if rotation is needed:
   - Read `LAST_SCHEDULED_ROTATION_DATE` variable
   - Calculate days since last scheduled rotation
   - If ≥ 14 days → proceed with rotation
   - If < 14 days → skip rotation (exit early)

2. **Run rotation** (if needed):
   - Load developers from Config sheet
   - Assign reviewers
   - Create new date column in sheet
   - ✅ Update `LAST_SCHEDULED_ROTATION_DATE` with today's date

3. **Skip rotation** (if not needed):
   - Log message: "Rotation not needed yet (X < 14 days)"
   - Workflow exits successfully
   - No changes to sheets
   - Variable remains unchanged

### Manual Runs (Triggered Manually)

When you trigger the workflow manually:
- ⏭️ **15-day check is skipped** (manual runs always execute)
- 📝 **Updates existing column** in sheet (doesn't create new column)
- ❌ **Does NOT update** `LAST_SCHEDULED_ROTATION_DATE`
- ✅ **Scheduled rotation cycle is unaffected**

## Example Timeline

```
Oct 15 (Wed) → Scheduled run ✅ (14+ days since last)
                → Rotation executes
                → Variable updated to: 2025-10-15

Oct 18 (Sat) → Manual run 🔧
                → Rotation executes (manual)
                → Variable stays: 2025-10-15 (unchanged)

Oct 22 (Wed) → Scheduled run ⏭️ (only 7 days since Oct 15)
                → Skipped (not yet due)
                → Variable stays: 2025-10-15

Oct 29 (Wed) → Scheduled run ✅ (14 days since Oct 15)
                → Rotation executes (every 2 Wednesdays!)
                → Variable updated to: 2025-10-29

Nov 05 (Wed) → Scheduled run ⏭️ (only 7 days since Oct 29)
                → Skipped (not yet due)
                → Variable stays: 2025-10-29

Nov 12 (Wed) → Scheduled run ✅ (14 days since Oct 29)
                → Rotation executes
                → Variable updated to: 2025-11-12
```

## Checking When Next Rotation is Due

### Option 1: Check GitHub Variable
1. Go to **Settings** → **Secrets and variables** → **Actions** → **Variables**
2. Find `LAST_SCHEDULED_ROTATION_DATE`
3. Add 14 days to see next rotation date (every 2 Wednesdays)

### Option 2: Check Workflow Logs
Look at the most recent scheduled workflow run:
- If rotation ran: Check the date column added to the sheet
- If rotation skipped: Check the log message for when it's due

### Option 3: Run Check Script Locally
```bash
# Set the date from GitHub Variable
export LAST_SCHEDULED_ROTATION_DATE="2025-10-29"

# Check if rotation is needed
poetry run python scripts/check_scheduled_rotation_needed.py
```

Output example:
```
📅 Last scheduled rotation: 2025-10-29
📊 Days since last scheduled rotation: 0
📏 Minimum days required: 14
⏳ Rotation not needed yet (0 < 14 days)
   Next rotation will be due on: 2025-10-29 + 14 days
```

## Troubleshooting

### Rotation ran too early (< 14 days)

**Possible causes:**
1. Variable was empty or had invalid date format
2. Variable was manually changed
3. Workflow file was modified incorrectly

**Solution:**
- Check the variable value in GitHub (Settings → Variables)
- Ensure format is `YYYY-MM-DD`
- Check workflow logs for the date check step

### Rotation didn't run after 14+ days

**Possible causes:**
1. Workflow is disabled
2. Repository is inactive (GitHub may pause scheduled workflows)
3. Variable has a future date

**Solution:**
- Check if workflow is enabled (Actions tab)
- Trigger a manual run to test
- Verify the variable date is correct

### Variable is not updating after rotation

**Possible causes:**
1. Workflow doesn't have permissions to update variables
2. GitHub token expired or insufficient permissions

**Solution:**
- Check workflow file has `permissions: actions: write`
- Verify `GITHUB_TOKEN` has repo access

## Migration from Old System

If you're migrating from the old system (checking sheet columns):

1. **Find last scheduled rotation date** from your sheet
   - Look at the most recent date column that was NOT a manual run
   - Format: `DD-MM-YYYY` in sheet → convert to `YYYY-MM-DD`

2. **Set the GitHub Variable**
   - Go to Settings → Secrets and variables → Actions → Variables
   - Create `LAST_SCHEDULED_ROTATION_DATE`
   - Set value to the converted date (e.g., `2025-10-15`)

3. **Deploy new workflow**
   - Push/merge the updated `.github/workflows/all-review-rotations.yml`
   - Next scheduled run will use the new system

## Technical Details

### Script Location
`scripts/check_scheduled_rotation_needed.py`

### Exit Codes
- `0`: Rotation needed (14+ days or first run)
- `1`: Rotation not needed yet (< 14 days)

### Variable Update
The workflow uses GitHub CLI (`gh variable set`) to update the variable after successful rotation:

```bash
gh variable set LAST_SCHEDULED_ROTATION_DATE --body "2025-10-29"
```

This requires:
- `GITHUB_TOKEN` (automatically provided in workflows)
- `permissions: actions: write` in workflow file

---

## Summary

| Feature | Old System | New System |
|---------|------------|------------|
| **Storage** | Sheet column headers | GitHub Variable |
| **Manual run impact** | ❌ Resets schedule | ✅ No impact |
| **Visibility** | ❌ Need to open sheet | ✅ Visible in GitHub UI |
| **Reliability** | ❌ Parse errors possible | ✅ Simple format |
| **Complexity** | ❌ Complex parsing | ✅ Simple date check |

**The new system is cleaner, more reliable, and separates scheduled from manual rotations!** 🎉

