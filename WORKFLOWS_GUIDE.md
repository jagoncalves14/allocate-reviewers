# GitHub Workflows Guide

## 🚀 Available Workflows

You have **3 workflows** to manage code review rotations:

### 1. **Run All Review Rotations** ⭐

**File:** `all-review-rotations.yml`

**What it does:**
- Processes **ALL sheets** listed in `SHEET_NAMES` variable
- Runs **BOTH** Individual Developers + Teams rotations
- This is your main workflow!

**Trigger:**
- ✅ **Scheduled:** Every Wednesday at 5:00 AM Finland Time (automatic)
- ✅ **Manual:** Click "Run workflow" in GitHub Actions

**When to use:**
- Regular rotations for all teams
- You want to update everything at once
- Scheduled automated runs

**Example:**
If your `SHEET_NAMES` variable contains:
```
Front End - Code Reviewers
Backend - Code Reviewers
Mobile - Code Reviewers
```

This workflow will process **ALL 3 sheets**, running **BOTH** devs + teams rotations for each.

---

### 2. **Single Sheet - Developers Rotation**

**File:** `single-sheet-devs-rotation.yml`

**What it does:**
- Processes **ONE specific sheet** (you choose)
- Runs **ONLY** Individual Developers rotation
- Prompts you to enter the sheet name

**Trigger:**
- ❌ **Scheduled:** No (manual only)
- ✅ **Manual:** Click "Run workflow" → Enter sheet name

**When to use:**
- Need to update developers for just one team
- Emergency rotation for specific team
- Testing a specific sheet

**How to use:**
1. Go to **Actions** tab
2. Select **"Single Sheet - Developers Rotation"**
3. Click **"Run workflow"**
4. Enter sheet name: `Front End - Code Reviewers`
5. Choose manual run mode (updates existing column) or scheduled mode (creates new column)
6. Click **"Run workflow"**

---

### 3. **Single Sheet - Teams Rotation**

**File:** `single-sheet-teams-rotation.yml`

**What it does:**
- Processes **ONE specific sheet** (you choose)
- Runs **ONLY** Teams rotation
- Prompts you to enter the sheet name

**Trigger:**
- ❌ **Scheduled:** No (manual only)
- ✅ **Manual:** Click "Run workflow" → Enter sheet name

**When to use:**
- Need to update teams for just one team
- Emergency team rotation for specific sheet
- Testing team rotation on specific sheet

**How to use:**
1. Go to **Actions** tab
2. Select **"Single Sheet - Teams Rotation"**
3. Click **"Run workflow"**
4. Enter sheet name: `Backend - Code Reviewers`
5. Choose manual run mode (updates existing column) or scheduled mode (creates new column)
6. Click **"Run workflow"**

---

## 📊 Quick Decision Guide

**Want to update everything?**
→ Use **"Run All Review Rotations"**

**Want to update devs for one specific team?**
→ Use **"Single Sheet - Developers Rotation"** + enter sheet name

**Want to update teams for one specific team?**
→ Use **"Single Sheet - Teams Rotation"** + enter sheet name

---

## 🎯 Common Scenarios

### Scenario 1: Regular Weekly Rotation
**Solution:** Do nothing! 
- "Run All Review Rotations" runs automatically every Wednesday
- Processes all sheets, all rotation types

### Scenario 2: Emergency Rotation for Frontend Team Only
**Solution:** Use "Single Sheet - Developers Rotation"
1. Go to Actions → "Single Sheet - Developers Rotation"
2. Enter: `Front End - Code Reviewers`
3. Run

### Scenario 3: Test New Sheet Before Adding to SHEET_NAMES
**Solution:** Use single-sheet workflows
1. Create and configure your new sheet
2. Test with "Single Sheet - Developers Rotation" first
3. Test with "Single Sheet - Teams Rotation" next
4. Once verified, add to `SHEET_NAMES` variable

### Scenario 4: Force Manual Rotation for All Teams
**Solution:** Use "Run All Review Rotations" manually
1. Go to Actions → "Run All Review Rotations"
2. Check "Manual run" checkbox
3. Run (updates existing columns instead of creating new)

---

## 🔧 Configuration

All workflows use:
- **Secret:** `GOOGLE_CREDENTIALS_JSON` (Service Account credentials)
- **Variable:** `SHEET_NAMES` (sheet name(s), one per line - works for single or multiple sheets)

**Single-sheet workflows accept:**
- Text input for sheet name (entered when you trigger the workflow)
- Boolean for manual run mode

---

## 📝 Notes

### Manual Run vs Scheduled Run

**Scheduled Run (default):**
- Creates a **new column** with today's date
- Example: Adds column "24-10-2025"

**Manual Run:**
- Updates the **existing column**
- Modifies header to show manual run date
- Example: Changes "22-10-2025" → "22-10-2025 / Manual Run on: 24-10-2025"
- Preserves the original sprint date for the 15-day schedule

### Sheet Name Format

When entering sheet names manually, use the **exact name** as it appears in Google Sheets:
- ✅ `Front End - Code Reviewers`
- ❌ `Front End - Code Reviewers ` (extra space)
- ❌ `front end - code reviewers` (wrong case)

---

## 🎉 Summary

You now have **3 simple workflows**:

1. **All-in-one:** Runs everything automatically (or manually)
2. **Devs-only:** Pick a sheet, run devs rotation
3. **Teams-only:** Pick a sheet, run teams rotation

Most of the time, you'll just let the scheduled workflow do its thing! 🚀

