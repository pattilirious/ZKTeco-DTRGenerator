# ZKTeco-DTRGenerator
Automatically generates Daily Time Record for the last two months without any use of software. Works with any ZKTeco devices or with any clones/rebrand as long as it's port 4370.

Instruction:
- Win + R and type powershell then press Enter

- Install these package:
pip install pyzk

- Run these command line >
cd "C:\Your folder's location\Biometrics Attendance Generator"
py export_logs.py

or make a desktop shortcut of Export DTR.bat (You can customize the icon the shortcut and rename it to whatever you like)

3. Open attendance.csv or if you did the shortcut, it will automatically open

4. Done

Notes:
- if generating again, make sure attendance.csv is closed before running the command.
- if you need to generate attendance from previous months or years, inside export_logs.py, change the number in MONTH_TO_EXPORT = ""
- don't rename or delete anything in the folder (except attendance.csv, it would just generate a new one after running the script).
