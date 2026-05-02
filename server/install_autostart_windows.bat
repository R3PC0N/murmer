@echo off
cd /d "%~dp0"

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS=%STARTUP%\MurmerWhisperServer.vbs
set BAT=%~dp0start_server.bat

echo Autostart instellen voor Murmer Whisper Server...

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run """%BAT%""", 0, False
) > "%VBS%"

echo Autostart ingesteld. De server start automatisch mee als Windows opstart.
echo Om te verwijderen: voer remove_autostart_windows.bat uit.
pause
