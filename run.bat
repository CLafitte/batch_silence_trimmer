@echo off
cd /d "%~dp0"
REM Launch Batch Silence Trimmer GUI
python "%~dp0batch_silence_trimmer.py"
echo.
pause
