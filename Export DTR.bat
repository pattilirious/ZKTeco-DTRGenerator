@echo off
  cd /d "%~dp0"
  py export_logs.py && start "" attendance.csv || pause