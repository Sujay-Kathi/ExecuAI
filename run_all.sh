#!/bin/bash

# ExecuAI - Startup Script for macOS
# This script starts both the Backend (FastAPI) and Frontend (Vite)

# Function to kill child processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping ExecuAI System..."
    # Kill all background jobs started by this script
    kill $(jobs -p) 2>/dev/null
    exit
}

# Trap Ctrl+C (SIGINT) and terminal closure (SIGTERM)
trap cleanup SIGINT SIGTERM

# Check if .venv exists in current directory
if [ ! -d ".venv" ]; then
    echo "❌ Error: .venv folder not found in current directory."
    echo "Please run this script from the project root directory."
    exit 1
fi

echo "🚀 Starting ExecuAI System..."

# 1. Start Backend
echo "📡 Starting Backend (FastAPI) on port 8000..."
# Using the python executable from the virtual environment
./.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --reload &
BACKEND_PID=$!

# 2. Wait for 5 seconds
echo "⏳ Waiting 5 seconds for backend to initialize..."
sleep 5

# 3. Start Frontend
echo "💻 Starting Frontend (Vite) on port 5173..."
# Check if vite binary exists in node_modules
if [ ! -f "frontend/node_modules/.bin/vite" ]; then
    echo "📦 Frontend dependencies or vite binary missing. Running npm install..."
    (cd frontend && npm install)
fi

# Navigate to frontend directory and run dev server in background
(cd frontend && npm run dev --host) &
FRONTEND_PID=$!

echo "✨ Both systems are now running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "--------------------------------------------------"
echo "Logs will appear below. Press Ctrl+C to stop both."
echo "--------------------------------------------------"

# Keep the script running to maintain the background processes
wait
