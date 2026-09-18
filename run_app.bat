@echo off
echo ===================================================
echo   UPI Transaction Control Center - Hackathon Launch
echo ===================================================
echo.
echo Starting FastAPI Backend Server on http://127.0.0.1:8000...
start cmd /k "cd backend && python start_backend.py"

echo Starting React + Vite Frontend App on http://localhost:3000...
start cmd /k "cd frontend && npm run dev"

echo.
echo Control Center is initializing!
echo Open http://localhost:3000 in your browser.
echo.
pause
