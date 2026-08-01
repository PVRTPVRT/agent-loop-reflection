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

pushd "%PROJECT_ROOT%"
"%PROJECT_ROOT%\.venv\Scripts\python.exe" -m agentloop.repository_experiment_cli ^
    --dataset benchmarks/datasets/repository-v0.5.json ^
    --experiment-id repository-v0.5-api-pilot-r6 ^
    --model gpt-5-nano-2025-08-07 ^
    --repetitions 5 ^
    --max-usd 0.07 ^
    --max-output-tokens 4000 ^
    --request-timeout 90 ^
    --output benchmarks/results/repository-v0.5-api-pilot-r6.json
set "COMMAND_EXIT=%ERRORLEVEL%"
popd
exit /b %COMMAND_EXIT%