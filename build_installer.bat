@echo off
echo === Building Murmer Installer ===
echo.

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not exist %ISCC% (
    echo ERROR: Inno Setup 6 not found.
    echo.
    echo Download and install it from:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

%ISCC% murmer.iss

if errorlevel 1 (
    echo.
    echo Build FAILED. Check the output above for errors.
) else (
    echo.
    echo Build successful!
    echo Installer: dist\Murmer-Setup-v1.0.exe
)

echo.
pause
