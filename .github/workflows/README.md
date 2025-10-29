# GitHub Actions Workflows

This directory contains automated workflows for the code review rotation system.

## Workflows

### 🧪 `tests.yml` - Automated Testing
**Triggers:**
- Every pull request to `master` or `main`
- Every push to `master` or `main`

**What it does:**
- ✅ Runs all tests with pytest
- 📊 Generates coverage reports
- 📤 Uploads coverage to Codecov (if configured)
- 🚀 Uses Poetry for dependency management
- 💾 Caches dependencies for faster runs

**Duration:** ~2-3 minutes

---

### 🔄 `all-review-rotations.yml` - All Review Rotations
Runs both individual developers and teams rotations for all configured sheets.

**Schedule:** Every Wednesday at 5:00 AM Finland Time (3:00 AM UTC)

---

### 👤 `single-sheet-devs-rotation.yml` - Single Sheet Developers Rotation
Runs individual developer allocation for a single sheet.

**Schedule:** Can be triggered manually

---

### 👥 `single-sheet-teams-rotation.yml` - Single Sheet Teams Rotation
Runs team-based reviewer assignment for a single sheet.

**Schedule:** Can be triggered manually

---

## Testing Workflow Details

The `tests.yml` workflow ensures code quality by:

1. **Running tests on every PR** - Catches issues before merge
2. **Running tests on push to main** - Ensures main branch is always healthy
3. **Caching dependencies** - Faster CI runs (< 1 min after first run)
4. **Coverage reporting** - Track test coverage over time

### Required for Merge?

To make tests required before merging:
1. Go to **Settings** → **Branches**
2. Add branch protection rule for `master`/`main`
3. Check "Require status checks to pass before merging"
4. Select "Run Tests" from the status checks

### Local Testing

Before pushing, run locally:
```bash
# Quick test
poetry run pytest tests/ -v

# With pre-commit hooks (auto-runs on commit)
poetry run pre-commit install
git commit -m "Your changes"
```

