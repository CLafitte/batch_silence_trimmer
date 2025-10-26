#!/bin/bash
# run.sh
# Launcher for Batch Silence Trimmer GUI

# Change to the directory where this script resides
cd "$(dirname "$0")" || {
  echo "Error: Failed to change directory."
  exit 1
}

# Launch the GUI
python3 batchsilencetrimmer.py || {
  echo "Error: Failed to start Batch Silence Trimmer."
  exit 1
}
