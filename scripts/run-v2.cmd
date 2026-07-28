@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."

for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%PROJECT_ROOT%\.env") do (
    set "%%A=%%B"
)

if not defined OPENAI_API_KEY (
    echo ERROR: Open .env and set OPENAI_API_KEY first. 1>&2
    exit /b 2
)

if "%~1"=="" (
    echo Usage: run-v2.cmd direct^|reflection^|adaptive [options] 1>&2
    exit /b 2
)

pushd "%PROJECT_ROOT%"
"%PROJECT_ROOT%\.venv\Scripts\python.exe" -m agentloop.main_v2 %*
set "COMMAND_EXIT=%ERRORLEVEL%"
popd
exit /b %COMMAND_EXIT%
