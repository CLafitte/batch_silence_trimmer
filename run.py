#!/usr/bin/env python3
"""
run.py
Launcher for Batch Silence Trimmer GUI.
Double-click or run to start silently (no console window).
"""

import os
import sys
import subprocess

# Ensure we're running from the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# If running on Windows via python.exe then re-launch under pythonw to hide console
if sys.platform.startswith("win") and "pythonw" not in sys.executable.lower():
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if os.path.exists(pythonw):
        subprocess.Popen([pythonw, os.path.abspath("batchsilencetrimmer.py")],
                         cwd=os.getcwd(), close_fds=True)
        sys.exit(0)

# Fallback to import and run normally
import batchsilencetrimmer
