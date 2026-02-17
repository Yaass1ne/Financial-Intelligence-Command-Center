@echo off
echo ==========================================
echo   FINCENTER - Clean Start
echo ==========================================

:: Kill any process on port 8080
echo [1/3] Clearing port 8080...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080 " ^| findstr "LISTENING"') do (
    echo     Killing PID %%a
    powershell -Command "Stop-Process -Id %%a -Force -ErrorAction SilentlyContinue"
)

:: Brief pause to let the port release
timeout /t 2 /nobreak >nul

:: Check Neo4j (Docker) is running
echo [2/3] Checking Neo4j...
curl -s http://localhost:7474 >nul 2>&1
if errorlevel 1 (
    echo     Neo4j not running - starting Docker containers...
    docker compose up -d neo4j
    echo     Waiting for Neo4j to be ready...
    timeout /t 10 /nobreak >nul
) else (
    echo     Neo4j is running OK
)

:: Start the API server
echo [3/3] Starting FINCENTER API on port 8080...
echo.
cd /d "%~dp0"
python -m src.api.main --port 8080
