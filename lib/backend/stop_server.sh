#!/bin/bash

# ============================================================================
# FRUIT DETECTION BACKEND SERVER - STOP SCRIPT
# ============================================================================

echo "🛑 Stopping Fruit Detection Backend Server..."

# Find and kill process on port 5000
PID=$(lsof -ti:5000 2>/dev/null)

if [ -z "$PID" ]; then
    echo "ℹ️  No server running on port 5000"
else
    kill $PID 2>/dev/null
    echo "✅ Server stopped (PID: $PID)"
fi

