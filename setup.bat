@echo off

set "batch_dir=%~dp0"
set "directory=%batch_dir%\dist"

echo %PATH% | find "%directory%" > nul
if %errorlevel% equ 0 (
    echo The directory is already in the user PATH.
) else (
    setx PATH "%PATH%;%directory%"
    echo Directory added to the user PATH.
)