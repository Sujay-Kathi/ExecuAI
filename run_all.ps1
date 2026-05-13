# ExecuAI - Startup Script
# This script starts both the Backend (FastAPI) and Frontend (Vite)

# Check if .venv exists in current directory
if (-not (Test-Path ".venv")) {
    Write-Host "❌ Error: .venv folder not found in current directory." -ForegroundColor Red
    Write-Host "Please run this script from the project root directory." -ForegroundColor Yellow
    exit
}

Write-Host "Starting ExecuAI System..." -ForegroundColor Cyan

# 1. Start Backend
Write-Host "Starting Backend (FastAPI) on port 8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload"

# 2. Wait for 5 seconds
Write-Host "Waiting 5 seconds for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 3. Start Frontend
Write-Host "Starting Frontend (Vite) on port 5173..." -ForegroundColor Green
Set-Location frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev"

Write-Host "Both systems are now running!" -ForegroundColor Cyan
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:5173"
