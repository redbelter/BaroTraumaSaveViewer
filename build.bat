@echo off
REM Build script for reverse-baro Windows executable
REM Requires: .venv with PySide6+PyInstaller installed
REM
REM Usage:
REM     build.bat
REM
REM Output: dist\reverse-baro\reverse-baro.exe  (double-click to run)

echo Building reverse-baro...
echo.

call .venv\Scripts\activate
pyinstaller --clean reverse-baro.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build succeeded!
    echo.
    echo Output: dist\reverse-baro\reverse-baro.exe
    dir dist\reverse-baro\reverse-baro.exe
) else (
    echo.
    echo Build FAILED (exit code: %ERRORLEVEL%)
)

pause
