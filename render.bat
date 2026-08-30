@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "RENDERCV=%SCRIPT_DIR%venv-CV\Scripts\rendercv.exe"

if not exist "%RENDERCV%" (
    echo Error: venv-CV not found at "%RENDERCV%".
    echo Run the setup steps in README.md first ^(python -m venv venv-CV, then pip install -r requirements.txt^).
    exit /b 1
)

set "CONTENT_YAML=%~1"
if "%CONTENT_YAML%"=="" set "CONTENT_YAML=render-cv-content.yaml"

"%RENDERCV%" render "%CONTENT_YAML%" --settings "%SCRIPT_DIR%render-cv-settings.yaml"

endlocal
