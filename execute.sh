#!/bin/bash

VIRTUAL_PATH=
SCRIPT_PATH=
source $VIRTUAL_PATH
cd $SCRIPT_PATH
poetry install
python scripts/rotate_devs_reviewers.py  # For individual developers
# python scripts/rotate_team_reviewers.py  # For teams
