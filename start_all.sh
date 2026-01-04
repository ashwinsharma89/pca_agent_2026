#!/bin/bash

# Get the directory where this script is located
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "🚀 Starting PCA Agent Services..."

# 1. Start Backend API in background
echo "Starting Backend API..."
source .venv312/bin/activate
# Run in background and redirect output to backend.log
python3 -m src.api.main > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# 2. Start Frontend in background
echo "Starting Frontend..."
cd frontend
# Run in background and redirect output to frontend.log
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

echo "✅ All services are starting in the background."
echo "   - API: http://localhost:8000"
echo "   - Web: http://localhost:3000"
echo "   - Logs: backend.log and frontend.log"

# Keep script alive for a moment to ensure processes don't die immediately
sleep 2

# Check if processes are still running
if ps -p $BACKEND_PID > /dev/null && ps -p $FRONTEND_PID > /dev/null; then
    echo "Double check: Services confirmed running."
else
    echo "⚠️ Warning: One or more services failed to start. Check the logs."
fi
