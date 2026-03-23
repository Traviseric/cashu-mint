@echo off
cd /d "C:\\code\\te-btc\\cashu-mint"

REM Clear API key to prevent fallback
set ANTHROPIC_API_KEY=

REM Token is injected by orchestrator at spawn-time; never write secrets to disk
if "%CLAUDE_CODE_OAUTH_TOKEN%"=="" (
    echo ERROR: CLAUDE_CODE_OAUTH_TOKEN is not set
    exit /b 1
)

REM Atomic credential swap (preserves mcpOAuth and other keys)
python "C:/code/orchestrator/src/orchestrator/tools/creds_swap.py" swap --lane-id "worker_001"

echo ========================================
echo MANAGED WORKER_001 v3.0.0
echo Interactive mode - manager controls tasks
echo ========================================
echo.

claude --dangerously-skip-permissions --model sonnet 2>"C:\\code\\te-btc\\cashu-mint\\.overnight\\worker_001_managed_stderr.log"
set CLAUDE_EXIT=%ERRORLEVEL%

REM Restore original credentials file
python "C:/code/orchestrator/src/orchestrator/tools/creds_swap.py" restore --lane-id "worker_001"

echo.
echo ========================================
echo MANAGED WORKER_001 session ended. Exit code: %CLAUDE_EXIT%
echo ========================================

REM Check stderr for rate limit signals
if exist "C:\\code\\te-btc\\cashu-mint\\.overnight\\worker_001_managed_stderr.log" (
    findstr /i /c:"hit your limit" /c:"rate-limit" /c:"resets" "C:\\code\\te-btc\\cashu-mint\\.overnight\\worker_001_managed_stderr.log" >nul 2>&1
    if not errorlevel 1 (
        echo MANAGED WORKER RATE LIMITED - see C:\\code\\te-btc\\cashu-mint\\.overnight\\worker_001_managed_stderr.log
    )
)
