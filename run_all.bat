@echo off
title ExecuAI Startup

:: Check if .venv exists in current directory
if not exist ".venv" (
    echo ❌ Error: .venv folder not found in current directory.
    echo Please run this script from the project root directory: c:\Users\R . Swati\OneDrive\Desktop\IDT\ExecuAI
    pause
    exit /b
)
echo 🚀 Starting ExecuAI System...

echo 📡 Starting Backend (FastAPI)...
start cmd /k ".\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --reload"

echo ⏳ Waiting 5 seconds...
timeout /t 5 /nobreak > nul

echo 💻 Starting Frontend (Vite)...
cd frontend
start cmd /k "npm run dev --host"

echo ✨ Both systems are now running!
pause
