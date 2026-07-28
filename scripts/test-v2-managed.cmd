@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."

pushd "%PROJECT_ROOT%"
"%PROJECT_ROOT%\.venv\Scripts\python.exe" -m ruff check src tests
if errorlevel 1 goto :failed

"%PROJECT_ROOT%\.venv\Scripts\python.exe" -m pytest -q ^
    --ignore=tests/test_sandbox.py ^
    --ignore=tests/test_docker_v2_integration.py
if errorlevel 1 goto :failed

"%PROJECT_ROOT%\.venv\Scripts\python.exe" -m pytest -q ^
    tests/test_managed_sandbox_v2.py
if errorlevel 1 goto :failed

popd
exit /b 0

:failed
set "COMMAND_EXIT=%ERRORLEVEL%"
popd
exit /b %COMMAND_EXIT%
