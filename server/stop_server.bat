@echo off
echo Murmer Whisper Server stoppen...
powershell -Command "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*faster_whisper_server*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Gestopt.
