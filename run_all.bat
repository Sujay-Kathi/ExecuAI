@echo off
title ExecuAI Startup
echo 🚀 Starting ExecuAI System...

echo 📡 Starting Backend (FastAPI)...
start cmd /k "python -m uvicorn backend.main:app --reload"

echo ⏳ Waiting 5 seconds...
timeout /t 5 /nobreak > nul

echo 💻 Starting Frontend (Vite)...
cd frontend
start cmd /k "npm run dev"

echo ✨ Both systems are now running!
pause
