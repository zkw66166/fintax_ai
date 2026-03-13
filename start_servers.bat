@echo off
echo Starting Fintax AI servers...
echo.

echo [1/2] Starting backend server on port 8000...
start "Backend Server" cmd /k "cd /d D:\fintax_ai && python -m uvicorn api.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend server...
start "Frontend Server" cmd /k "cd /d D:\fintax_ai\frontend && npm run dev"

echo.
echo ========================================
echo Servers are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173 (or next available port)
echo ========================================
echo.
echo Press any key to exit this window (servers will keep running)
pause >nul
