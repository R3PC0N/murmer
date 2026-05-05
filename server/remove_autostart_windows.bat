@echo off
set VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\MurmurWhisperServer.vbs

if exist "%VBS%" (
    del "%VBS%"
    echo Autostart verwijderd.
) else (
    echo Autostart was niet ingesteld.
)
pause
