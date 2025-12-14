.PHONY: dev backend frontend stop clean logs help

help:
	@echo "Expense Tracker Development Commands"
	@echo "===================================="
	@echo "make dev       - Start both backend and frontend"
	@echo "make backend   - Start only backend"
	@echo "make frontend  - Start only frontend"
	@echo "make stop      - Stop all running services"
	@echo "make clean     - Clean logs and temporary files"
	@echo "make logs      - Show recent logs"

dev:
	@echo "🚀 Starting development environment..."
	@./start-dev.sh

backend:
	@echo "Starting backend..."
	@cd backend && source venv/bin/activate && set -a && source .env && set +a && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	@echo "Starting frontend..."
	@cd frontend && npm run dev

stop:
	@echo "Stopping services..."
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@lsof -ti:5173 | xargs kill -9 2>/dev/null || true
	@echo "✅ Services stopped"

clean:
	@echo "Cleaning logs..."
	@rm -f backend.log frontend.log
	@echo "✅ Cleaned"

logs:
	@echo "=== Backend Logs ==="
	@tail -20 backend.log 2>/dev/null || echo "No backend logs"
	@echo ""
	@echo "=== Frontend Logs ==="
	@tail -20 frontend.log 2>/dev/null || echo "No frontend logs"
