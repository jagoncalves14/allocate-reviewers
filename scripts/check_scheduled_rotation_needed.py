"""
Check if a scheduled rotation is needed based on GitHub Variable.

This script checks the LAST_SCHEDULED_ROTATION_DATE GitHub Variable
to determine if 15 days have passed since the last scheduled rotation.

Exit codes:
    0: Rotation needed (15+ days since last rotation or first run)
    1: Rotation not needed yet (< 15 days)

Environment Variables:
    LAST_SCHEDULED_ROTATION_DATE: Date of last scheduled rotation (format: YYYY-MM-DD)
                                  If empty/missing, assumes first run (rotation needed)
"""

import os
import sys
from datetime import datetime

MINIMUM_DAYS_BETWEEN_ROTATIONS = 14  # 2 weeks (Wednesday to Wednesday)


def main() -> None:
    """
    Check if scheduled rotation is needed based on GitHub Variable.

    Returns:
        Exit code 0 if rotation needed, 1 if not needed yet
    """
    # Get last scheduled rotation date from environment
    last_date_str = os.environ.get("LAST_SCHEDULED_ROTATION_DATE", "").strip()

    if not last_date_str:
        print("✅ No previous scheduled rotation found - rotation is needed")
        print("   (This appears to be the first scheduled run)")
        sys.exit(0)

    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
        print(f"📅 Last scheduled rotation: {last_date.strftime('%Y-%m-%d')}")
    except ValueError:
        print(
            f"⚠️  Warning: Invalid date format in LAST_SCHEDULED_ROTATION_DATE: '{last_date_str}'"
        )
        print("   Expected format: YYYY-MM-DD")
        print("   Treating as first run - rotation is needed")
        sys.exit(0)

    # Calculate days since last rotation
    today = datetime.now()
    days_since = (today - last_date).days

    print(f"📊 Days since last scheduled rotation: {days_since}")
    print(f"📏 Minimum days required: {MINIMUM_DAYS_BETWEEN_ROTATIONS}")

    if days_since >= MINIMUM_DAYS_BETWEEN_ROTATIONS:
        print(
            f"✅ Rotation needed ({days_since} >= {MINIMUM_DAYS_BETWEEN_ROTATIONS} days)"
        )
        sys.exit(0)
    else:
        print(
            f"⏳ Rotation not needed yet ({days_since} < {MINIMUM_DAYS_BETWEEN_ROTATIONS} days)"
        )
        print(
            f"   Next rotation will be due on: {last_date.strftime('%Y-%m-%d')} + {MINIMUM_DAYS_BETWEEN_ROTATIONS} days"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
