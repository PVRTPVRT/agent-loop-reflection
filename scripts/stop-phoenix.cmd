@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."

for /f "delims=" %%S in ('docker inspect --format "{{.State.Running}}" agentloop-phoenix 2^>nul') do set "LEGACY_RUNNING=%%S"
if /I "%LEGACY_RUNNING%"=="true" (
    docker stop agentloop-phoenix
    if errorlevel 1 exit /b 1
)

pushd "%PROJECT_ROOT%"
docker compose -f compose.observability.yaml stop
set "COMMAND_EXIT=%ERRORLEVEL%"
popd

if "%COMMAND_EXIT%"=="0" echo Phoenix stopped. Persistent Compose data was preserved.
exit /b %COMMAND_EXIT%
