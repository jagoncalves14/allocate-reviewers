#!/bin/bash

VIRTUAL_PATH=
SCRIPT_PATH=
source $VIRTUAL_PATH
cd $SCRIPT_PATH
poetry install
python allocate_reviewers.py #or rotate_reviewers.py
