# Complete Migration Guide

## 🎯 Overview

This guide covers **ALL changes** from the original version to the current version, including:
- Column renames (for clarity)
- Column deletions (removed unused/obsolete columns)
- New Config sheet (centralized configuration)
- Sheet reordering (Config becomes first sheet)
- GitHub Secrets cleanup (moved configuration to Google Sheets)

### Philosophy Behind Changes

**🎯 Main Goal:** Move configuration from GitHub Secrets → Google Sheets

**Why?**
1. **Accessibility:** Non-technical team members can update configuration
2. **Simplicity:** No need to navigate GitHub repository settings
3. **Single Source of Truth:** All data in one place (Google Sheets)
4. **Better UX:** Edit configuration alongside the data it affects
5. **Reduced Complexity:** Fewer GitHub Secrets to manage

## 📋 Complete List of Changes

### **Individual Developers Sheet (FE Devs)**

**Column Changes:**

| Old Column Name | New Column Name | Status |
|----------------|-----------------|--------|
| `Reviewer Number` | `Number of Reviewers` | ✏️ Renamed |
| `Indexes` | `Preferable Reviewers` | ✏️ Renamed |

**Current Structure:**
```
A: Developer
B: Number of Reviewers
C: Preferable Reviewers
D+: Date columns (e.g., 23-10-2025)
```

### **Teams Sheet**

**Column Changes:**

| Old Column Name | New Column Name | Status |
|----------------|-----------------|--------|
| `Default Developer` | `Team Developers` | ✏️ Renamed |
| `Reviewer Number` | `Number of Reviewers` | ✏️ Renamed |
| `Indexes` | *(removed)* | ❌ Deleted ([Why?](#why-was-reviewers_config_list-removed-what-was-the-logic-refactoring)) |

**Current Structure:**
```
A: Team
B: Team Developers
C: Number of Reviewers
D+: Date columns (e.g., 23-10-2025)
```

### **New Config Sheet**

**Status:** 🆕 NEW - Must be created

**Structure:**
```
A: Experienced Developers (list from A2 onwards)
B: Default Number of Reviewers (value in B2)
```

### **Sheet Order Change**

**Before:**
1. Individual Developers (index 0)
2. Teams (index 1)

**After:**
1. Config (index 0) - NEW
2. Individual Developers (index 1)
3. Teams (index 2)

---

## 🚀 Step-by-Step Migration

### Step 1: Rename Columns in Individual Developers Sheet

1. Go to your **FE Devs** (or Individual Developers) sheet
2. Update the header row:
   - Cell B1: Change `Reviewer Number` → `Number of Reviewers`
   - Cell C1: Change `Indexes` → `Preferable Reviewers`

### Step 2: Update Columns in Teams Sheet

1. Go to your **Teams** sheet
2. Update the header row:
   - Cell B1: Change `Default Developer` → `Team Developers`
   - Cell C1: Change `Reviewer Number` → `Number of Reviewers`
3. **Delete Column D** (`Indexes` column - no longer needed)

### Step 3: Create Config Sheet

1. **Insert a new sheet** at the beginning
2. Name it "Config" (or any name you prefer)
3. **Option A: Empty Config (uses defaults)**
   - Just create an empty sheet - that's it!
   - System will use: `reviewer_number=1`, `experienced_devs=empty`
   
4. **Option B: Populate Config (recommended)**
   - Set up the structure:

```
     A                        |  B
1    Experienced Developers   |  Default Number of Reviewers
2    Dev2                     |  2
3    Dev3                     |
4    Dev4                     |
5    Dev5                     |
6    Dev6                     |
7    Dev7                     |
8    Dev8                     |
9    Dev9                     |
10   Dev10                    |
11   Dev11                    |
```

**Important:**
- Column A: List ALL experienced developers (one per row, starting from A2)
- Cell B2: Enter the default number of reviewers (e.g., `2`)
- Names must match **exactly** with names in your other sheets

### Step 4: Reorder Sheets

Drag the sheet tabs at the bottom to ensure this order:
1. **Config** (must be first)
2. **Individual Developers / FE Devs** (must be second)
3. **Teams** (must be third)

### Step 5: Clean Up GitHub Secrets

Go to GitHub → Repository Settings → Secrets and Variables → Actions

**Delete these secrets (no longer needed):**

- ❌ **`DEFAULT_REVIEWER_NUMBER`**
  - **Why removed:** This configuration is now stored in the Config sheet (Cell B2)
  - **Benefit:** Non-technical team members can update it without GitHub access
  - **Where it is now:** Config sheet, Cell B2

- ❌ **`EXPERIENCED_DEV_NAMES`**
  - **Why removed:** This list is now stored in the Config sheet (Column A, from A2 onwards)
  - **Benefit:** Easy to add/remove experienced developers without touching GitHub
  - **Where it is now:** Config sheet, Column A (starting from A2)

- ❌ **`REVIEWERS_CONFIG_LIST`**
  - **Why removed:** The rotation logic was completely refactored and no longer uses index-based configuration
  - **Old system:** Used the "Indexes" column to manually specify which reviewers to assign
  - **New system:** Automatically assigns reviewers based on team composition (member count)
  - **Status:** Completely obsolete with the new logic
  - 📖 **[See FAQ: Why was REVIEWERS_CONFIG_LIST removed?](#why-was-reviewers_config_list-removed-what-was-the-logic-refactoring)** for detailed explanation

**Keep these secrets:**
- ✅ `GOOGLE_CREDENTIALS_JSON` - Required for authentication with Google Sheets API
- ✅ `SHEET_NAME` - Required to identify which Google Sheet to use

---

### 📊 GitHub Secrets: Before vs After

**BEFORE (Old System):**
```
1. GOOGLE_CREDENTIALS_JSON
2. SHEET_NAME
3. DEFAULT_REVIEWER_NUMBER       ❌ → Moved to Config sheet
4. EXPERIENCED_DEV_NAMES          ❌ → Moved to Config sheet
5. REVIEWERS_CONFIG_LIST          ❌ → Obsolete (logic refactored)
```

**AFTER (New System):**
```
1. GOOGLE_CREDENTIALS_JSON        ✅ Still needed
2. SHEET_NAME                     ✅ Still needed
```

**Result:** 5 secrets → 2 secrets 🎉

### Step 6: Test the Setup

**Option A: Test Locally**
```bash
export SHEET_NAME="your-sheet-name"
export CREDENTIAL_FILE="credentials.json"

# Test Individual Developers rotation
poetry run python scripts/rotate_devs_reviewers.py

# Test Teams rotation
poetry run python scripts/rotate_team_reviewers.py
```

**Option B: Test via GitHub Actions**
1. Go to Actions → "Individual Developers Review Rotation"
2. Click "Run workflow"
3. Verify success and check the Google Sheet

---

## 📊 Before vs After Comparison

### Individual Developers Sheet

**BEFORE:**
```
| Developer | Reviewer Number | Indexes      | 23-10-2025      | ...
|-----------|----------------|--------------|-----------------|----
| Dev3      | 2              | 12, 7        | Dev8, ...       | ...
| Dev2      | 2              | 12, 7        | Dev8, ...       | ...
```

**AFTER:**
```
| Developer | Number of Reviewers | Preferable Reviewers | 23-10-2025      | ...
|-----------|---------------------|----------------------|-----------------|----
| Dev3      | 2                   | 12, 7                | Dev8, ...       | ...
| Dev2      | 2                   | 12, 7                | Dev8, ...       | ...
```

### Teams Sheet

**BEFORE:**
```
| Team       | Default Developer   | Reviewer Number | Indexes | 23-10-2025    | ...
|------------|---------------------|-----------------|---------|---------------|----
| Team1      | Dev5, Dev2, Dev10   | 2               | 0, 1    | Dev3, Dev2    | ...
| Team2      | Dev3                | 2               | 0, 9    | Dev3, Dev10   | ...
```

**AFTER:**
```
| Team       | Team Developers     | Number of Reviewers | 23-10-2025    | ...
|------------|---------------------|---------------------|---------------|----
| Team1      | Dev5, Dev2, Dev10   | 2                   | Dev3, Dev2    | ...
| Team2      | Dev3                | 2                   | Dev3, Dev10   | ...
```

### Config Sheet (NEW)

**AFTER (new sheet):**
```
| Experienced Developers | Default Number of Reviewers |
|------------------------|------------------------------|
| Dev2                   | 2                            |
| Dev3                   |                              |
| Dev4                   |                              |
| Dev5                   |                              |
| Dev6                   |                              |
| Dev7                   |                              |
| Dev8                   |                              |
| Dev9                   |                              |
| Dev10                  |                              |
| Dev11                  |                              |
```

---

## ❓ Troubleshooting

### "Unknown headers" error

**Error:** `GSpreadException: the given 'expected_headers' contains unknown headers`

**Solution:** Make sure you've renamed ALL columns exactly as shown above:
- Individual Developers: `Number of Reviewers`, `Preferable Reviewers`
- Teams: `Team Developers`, `Number of Reviewers`

### "Config sheet is empty or missing data"

**Solution:** 
- Ensure Config sheet is the **first sheet** (index 0)
- Cell B2 must contain a number (e.g., `2`)
- Column A must have developer names starting from A2

### Wrong sheet order error

**Solution:** Drag tabs at the bottom to ensure:
1. Config (first)
2. Individual Developers (second)
3. Teams (third)

### Names don't match

**Solution:** Developer names in Config sheet Column A must match **exactly** with:
- Names in Individual Developers sheet (Column A)
- Names in Teams sheet "Team Developers" column
- Check for typos, extra spaces, or wrong capitalization

---

## 🎉 Benefits of New Structure

- ✨ **No GitHub Secrets** - Configuration in Google Sheets
- 📝 **Easier Updates** - Just edit the sheet
- 🔍 **Clearer Names** - More descriptive column headers
- 🚮 **Less Clutter** - Removed unused "Indexes" column from Teams
- 👥 **Team-Friendly** - Non-developers can manage config

---

## 🔄 Quick Reference

### Column Name Changes Summary

| Sheet | Old Name | New Name | Action |
|-------|----------|----------|--------|
| Individual Developers | `Reviewer Number` | `Number of Reviewers` | Rename |
| Individual Developers | `Indexes` | `Preferable Reviewers` | Rename |
| Teams | `Default Developer` | `Team Developers` | Rename |
| Teams | `Reviewer Number` | `Number of Reviewers` | Rename |
| Teams | `Indexes` | *(none)* | Delete |
| **Config** | *(new sheet)* | - | Create |

### Required Sheet Order

1. 🆕 **Config** (index 0)
2. 📋 **Individual Developers** (index 1)
3. 👥 **Teams** (index 2)

---

## 💾 Rollback Instructions

If you need to revert to the old system:

1. **Undo column renames** in both sheets
2. **Re-add the Indexes column** to Teams sheet
3. **Delete the Config sheet**
4. **Re-add GitHub Secrets:**
   - `DEFAULT_REVIEWER_NUMBER=2`
   - `EXPERIENCED_DEV_NAMES=Dev2, Dev3, Dev4, Dev5, Dev6, Dev7, Dev8, Dev9, Dev10, Dev11`
   - `REVIEWERS_CONFIG_LIST=` (if you were using the old index-based system)
5. **Revert code changes:**
   ```bash
   git revert HEAD
   git push
   ```

---

## ✅ Migration Checklist

Use this checklist to ensure you've completed all steps:

- [ ] Renamed `Reviewer Number` → `Number of Reviewers` in Individual Developers sheet
- [ ] Renamed `Indexes` → `Preferable Reviewers` in Individual Developers sheet
- [ ] Renamed `Default Developer` → `Team Developers` in Teams sheet
- [ ] Renamed `Reviewer Number` → `Number of Reviewers` in Teams sheet
- [ ] Deleted `Indexes` column from Teams sheet
- [ ] Created new Config sheet with proper structure
- [ ] Added experienced developer names to Config sheet (Column A, from A2)
- [ ] Added default reviewer number to Config sheet (Cell B2)
- [ ] Reordered sheets: Config (1st), Individual Developers (2nd), Teams (3rd)
- [ ] Deleted `DEFAULT_REVIEWER_NUMBER` secret from GitHub
- [ ] Deleted `EXPERIENCED_DEV_NAMES` secret from GitHub
- [ ] Deleted `REVIEWERS_CONFIG_LIST` secret from GitHub (if it exists)
- [ ] Tested with a manual workflow run
- [ ] Verified reviewers were assigned correctly

---

## ❓ FAQ (Frequently Asked Questions)

### Why was `REVIEWERS_CONFIG_LIST` removed? What was the "logic refactoring"?

**The Old System (Index-Based):**

The old Teams rotation used a manual, index-based configuration system:

1. **`REVIEWERS_CONFIG_LIST` Secret:** Contained a list like `"0,1;2,3;4,5"` where numbers corresponded to developer indexes
2. **`Indexes` Column:** Each team had an "Indexes" column (e.g., `"0, 1"`) pointing to specific reviewers
3. **Manual Assignment:** You had to manually configure which reviewer indexes to use for each team

**Example of Old System:**
```
Team: Team1
Indexes: 0, 1

Where:
- 0 = First developer in the list (e.g., Dev3)
- 1 = Second developer in the list (e.g., Dev2)

So Team1 would always get Dev3 and Dev2 as reviewers.
```

**Problems with Old System:**
- ❌ **Manual maintenance:** Had to update indexes every time you added/removed developers
- ❌ **Not intuitive:** Index numbers aren't clear (who is "0"? who is "5"?)
- ❌ **Prone to errors:** Wrong index = wrong reviewer
- ❌ **Not load-balanced:** Same reviewers could be assigned to multiple teams
- ❌ **Requires GitHub access:** Non-technical users couldn't update configuration

---

**The New System (Team Composition-Based):**

The new Teams rotation is **automatic and intelligent**:

1. **No manual configuration needed** - Logic is based on team composition
2. **Automatically balances load** - Distributes assignments evenly across experienced developers
3. **No indexes needed** - Uses actual developer names from Teams sheet

**How New Logic Works:**

```
For each team, check the "Team Developers" column:

├─ Team has 0 members?
│  └─ Assign N random experienced developers (not from any team)
│
├─ Team has < N members? (where N = "Number of Reviewers")
│  ├─ Use ALL team members as reviewers
│  └─ Fill remaining slots with experienced developers (excluding team members)
│
└─ Team has >= N members?
   └─ Randomly select N members from the team
```

**Example of New System:**
```
Team: Team1
Team Developers: Dev5, Dev2, Dev10
Number of Reviewers: 2

Logic:
→ Team has 3 members, needs 2 reviewers
→ Randomly select 2 from [Dev5, Dev2, Dev10]
→ Result: Dev2, Dev10 (for this rotation)
```

**Benefits of New System:**
- ✅ **Fully automatic** - No manual configuration needed
- ✅ **Load balanced** - Assignments distributed evenly
- ✅ **Self-explanatory** - Uses real names, not cryptic indexes
- ✅ **Dynamic** - Adapts to team changes automatically
- ✅ **Fair rotation** - Everyone gets equal review opportunities

---

### Do I need to do anything to migrate from the old logic to the new logic?

**No code changes needed!** Just follow the migration steps:

1. Delete the `Indexes` column from Teams sheet
2. Delete the `REVIEWERS_CONFIG_LIST` secret from GitHub
3. The new logic will automatically take over

The new system uses the existing `Team Developers` column to determine assignments.

---

### What if I want specific reviewers for a specific team?

The new system doesn't support manually pinning specific reviewers to teams. Instead, it uses:

- **Team members** (from "Team Developers" column) when the team has members
- **Experienced developers** (from Config sheet) when the team needs more reviewers

If you need custom logic, you would need to modify `scripts/rotate_team_reviewers.py`.

---

### Can I still use the "Number of Reviewers" column per team?

**Yes!** ✅ Each team can specify its own "Number of Reviewers" in Column C. If empty, it uses the default from the Config sheet (Cell B2).

**Example:**
```
| Team       | Team Developers | Number of Reviewers | ...
|------------|-----------------|---------------------|----
| Team1      | Dev5, Dev2      | 3                   | ... (3 reviewers)
| Team2      | Dev3            |                     | ... (uses default: 2)
| Team3      | Dev1            | 1                   | ... (1 reviewer)
```

---

### Are all three sheets required?

**Two sheets must exist, one is optional:**

- **Config Sheet (index 0)** - ✅ **Must exist, but content is optional**
  - **The sheet itself MUST exist** (to keep indices consistent)
  - **Content is completely optional** - can be blank/empty
  - If empty or columns missing: Uses defaults (reviewer_number=1, experienced_devs=empty)
  - If populated: Loads your custom configuration
  - **Why required?** So Individual Developers is always at index 1, Teams at index 2

- **Individual Developers (index 1)** - ✅ **Required with content**
  - This is the main sheet for developer rotations
  - Must have proper structure and content
  - Without this, the rotation won't work

- **Teams Sheet (index 2)** - 🔵 **Optional (can be omitted entirely)**
  - If missing: Teams rotation is skipped silently
  - If present: Teams rotation runs normally
  - **Perfect for gradual adoption!**

**Minimum Setup:**
1. **Create Config sheet** (first tab) - Can be completely empty
2. **Create Individual Developers sheet** (second tab) - Must have content
3. *(Optional)* **Create Teams sheet** (third tab) - Only if you need it

**Example of minimal Config sheet:**
```
Just create an empty sheet tab named "Config" - that's it!
No headers, no data needed. System will use defaults.
```

The system gracefully handles empty Config sheets and missing Teams sheets.

---

**Need help?** Check the troubleshooting section or review the before/after comparison above.

