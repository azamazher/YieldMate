#!/bin/bash

# ============================================================================
# FRUIT DETECTION BACKEND SERVER - START SCRIPT
# ============================================================================

echo "🚀 Starting Fruit Detection Backend Server..."
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found. Please install Python 3."
    exit 1
fi

# Check if dependencies are installed
echo "📦 Checking dependencies..."
python3 -c "import flask, ultralytics, PIL" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Missing dependencies. Installing..."
    pip3 install flask flask-cors ultralytics pillow
fi

# Check if port 5000 is already in use
if lsof -ti:5000 &> /dev/null; then
    echo "⚠️  Port 5000 is already in use."
    echo "   Stopping existing server..."
    lsof -ti:5000 | xargs kill 2>/dev/null
    sleep 1
fi

# Navigate to project root (two levels up from lib/backend/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Start the server from lib/backend directory
echo "✅ Starting server on http://localhost:5000"
echo "   Press Ctrl+C to stop the server"
echo ""
python3 lib/backend/backend_server_example.py

