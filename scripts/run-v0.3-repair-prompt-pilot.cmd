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

set "MAX_CODING_ROUNDS=2"

pushd "%PROJECT_ROOT%"
"%PROJECT_ROOT%\.venv\Scripts\python.exe" -m agentloop.repair_replay_v2_cli ^
    --dataset benchmarks/datasets/coding-v2-repair-pilot-r2.json ^
    --routing benchmarks/routing/coding-v2-repair-routing.json ^
    --contracts benchmarks/contracts/coding-v2-repair-contracts.json ^
    --candidate benchmarks/fixtures/ttl-lru-expiry-order-bug.py ^
    --model gpt-5.4-nano ^
    --reasoning-effort none ^
    --request-timeout 60 ^
    --max-retries 0 ^
    --output benchmarks/results/repair-replay-v0.3-prompt-hardening.json ^
    --trace-dir benchmarks/traces/repair-replay-v0.3-prompt-hardening
set "COMMAND_EXIT=%ERRORLEVEL%"
popd
exit /b %COMMAND_EXIT%
