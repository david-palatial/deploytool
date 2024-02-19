@echo off
set "batch_dir=%~dp0"
set "directory=%batch_dir%\dist"

if not "%PATH%" == "%PATH:;%directory;=%" (
    echo Setup complete *2.
) else (
    setx PATH "%directory%;%PATH%" /M
    echo Setup complete *1.
)