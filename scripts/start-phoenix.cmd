@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
set "PHOENIX_URL=http://localhost:6006/projects?timeRangeKey=7d"

docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop is not running. Start Docker Desktop and run this script again. 1>&2
    exit /b 2
)

for /f "delims=" %%S in ('docker inspect --format "{{.State.Running}}" agentloop-phoenix 2^>nul') do set "LEGACY_RUNNING=%%S"
if /I "%LEGACY_RUNNING%"=="true" (
    echo INFO: Reusing the existing agentloop-phoenix container.
    start "" "%PHOENIX_URL%"
    exit /b 0
)

pushd "%PROJECT_ROOT%"
docker compose -f compose.observability.yaml up -d --wait
set "COMMAND_EXIT=%ERRORLEVEL%"
popd

if not "%COMMAND_EXIT%"=="0" (
    echo ERROR: Phoenix did not become healthy. Check: docker compose -f compose.observability.yaml logs 1>&2
    exit /b %COMMAND_EXIT%
)

start "" "%PHOENIX_URL%"
echo Phoenix is ready at http://localhost:6006
exit /b 0
