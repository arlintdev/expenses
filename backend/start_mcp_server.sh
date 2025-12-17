#!/bin/bash

set -e

echo "🚀 Starting Expenses MCP OAuth Server"
echo "===================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9 or later."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Please create one with:"
    echo "   - GOOGLE_CLIENT_ID"
    echo "   - GOOGLE_CLIENT_SECRET"
    echo "   - JWT_SECRET_KEY"
    echo "   - DATABASE_URL"
    exit 1
fi

# Load environment
set -a
source .env
set +a

# Set defaults
export BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
export MCP_SERVER_URL="${MCP_SERVER_URL:-http://localhost:8001}"
export PYTHONUNBUFFERED=1

echo "Configuration:"
echo "  Backend URL: $BACKEND_URL"
echo "  MCP Server URL: $MCP_SERVER_URL"
echo "  Python: $(python3 --version)"
echo ""

# Check if venv exists, create if not
if [ ! -d venv ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✨ Starting MCP OAuth Server on $MCP_SERVER_URL"
echo "===================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the server
python3 mcp_oauth_server.py
