@echo off
setlocal
cd /d %~dp0
python -m pip install --upgrade pyinstaller
pyinstaller --noconfirm --onedir --windowed --name Complaint_Service_Hub_Launcher ^
  --hidden-import=tkinter ^
  --hidden-import=tkinter.ttk ^
  --hidden-import=tkinter.filedialog ^
  --hidden-import=tkinter.messagebox ^
  --hidden-import=tkinter.scrolledtext ^
  launcher.py
xcopy /E /I /Y config dist\Complaint_Service_Hub_Launcher\config
xcopy /E /I /Y masters dist\Complaint_Service_Hub_Launcher\masters
xcopy /E /I /Y templates dist\Complaint_Service_Hub_Launcher\templates
xcopy /E /I /Y profiles dist\Complaint_Service_Hub_Launcher\profiles
if exist resources xcopy /E /I /Y resources dist\Complaint_Service_Hub_Launcher\resources
copy /Y hub_app.py dist\Complaint_Service_Hub_Launcher\hub_app.py
copy /Y launcher.py dist\Complaint_Service_Hub_Launcher\launcher.py
copy /Y main.py dist\Complaint_Service_Hub_Launcher\main.py
copy /Y manifest.json dist\Complaint_Service_Hub_Launcher\manifest.json
copy /Y app_version.json dist\Complaint_Service_Hub_Launcher\app_version.json
mkdir dist\Complaint_Service_Hub_Launcher\logs 2>nul
mkdir dist\Complaint_Service_Hub_Launcher\records 2>nul
mkdir dist\Complaint_Service_Hub_Launcher\updates 2>nul
mkdir dist\Complaint_Service_Hub_Launcher\backups 2>nul
echo Build completed.
pause
