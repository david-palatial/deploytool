@echo off
setlocal EnableDelayedExpansion

set "batch_dir=%~dp0"
set "directory=%batch_dir%dist"

echo %PATH% | find "%directory%" > nul
if %errorlevel% equ 0 (
    echo The directory is already in the user PATH.
) else (
    set PATH="%PATH%;%directory%" > nul
    echo Directory added to the user PATH.

    @"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
    %directory%\sps-app.exe setup
)

endlocal