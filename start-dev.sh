#!/bin/bash

# Start script for Expense Tracker development environment

echo "🚀 Starting Expense Tracker Development Environment"
echo ""

# Kill any existing processes on the ports
echo "Checking for existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

echo "✅ Ports cleared"
echo ""

# Start backend in background
echo "Starting backend on http://localhost:8000..."
cd backend
source venv/bin/activate
set -a
source .env
set +a
uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo "✅ Backend started (PID: $BACKEND_PID)"
echo "   Logs: tail -f backend.log"
echo ""

# Start frontend in background
echo "Starting frontend on http://localhost:5173..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo "✅ Frontend started (PID: $FRONTEND_PID)"
echo "   Logs: tail -f frontend.log"
echo ""

echo "================================================"
echo "🎉 Development environment ready!"
echo "================================================"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""
echo "To stop all services:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "To view logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo "================================================"

# Keep script running
wait
