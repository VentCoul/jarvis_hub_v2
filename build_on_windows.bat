@echo off
echo ====================================================
echo   JARVIS HUB V2: EXE BUILDER (Windows)
echo ====================================================
echo.

echo [1/3] Installing/Updating dependencies...
python -m pip install --upgrade pip
python -m pip install customtkinter pandas openpyxl xlrd pillow pyinstaller

echo.
echo [2/3] Cleaning up old builds...
if exist build rd /s /q build
if exist dist rd /s /q dist
if exist *.spec del /f /q *.spec

echo.
echo [3/3] Building Standalone EXE...
echo (This may take a few minutes due to pandas/openpyxl)
python -m PyInstaller --noconsole --onefile ^
    --collect-all customtkinter ^
    --hidden-import pandas ^
    --hidden-import openpyxl ^
    --add-data "modules;modules" ^
    --name "Jarvis_Retail_HUB_v2.10" ^
    jarvis_hub.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo ====================================================
    echo   SUCCESS! Check 'dist' folder for Jarvis_Retail_HUB_v2.exe
    echo ====================================================
) else (
    echo.
    echo !!!!!!!!!!!!!!! BUILD FAILED !!!!!!!!!!!!!!!
    echo Check the error messages above.
)

pause
