# ZKTeco-DTRGenerator
Automatically generates Daily Time Record without any use of software. Works with any ZKTeco devices or with any clones/rebrand as long as it's port 4370.

Instructions:
- Download Python from https://www.python.org/
  
- Win + R and type powershell then press Enter

- Install this package:
pip install pyzk

- Run these command line >
cd "C:\Your folder's location\ZKTeco-DTRGenerator"
and py export_logs.py

or make a desktop shortcut of Export DTR.bat (You can customize the icon the shortcut and rename it to whatever you like)

- Open attendance.csv or if you did the shortcut, it will automatically open

- Done

Notes:
- if generating again, make sure attendance.csv is closed before running the command/BAT file.
- don't rename or delete anything in the folder (except attendance.csv, it would just generate a new one after running the script).
