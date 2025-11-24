#!/bin/bash

# Script to run Flutter app on Android emulator
# Usage: ./run_android.sh [device_id]

DEVICE="${1:-emulator-5554}"

echo "🚀 Running Fruit Detection app on Android..."
echo "📱 Device: $DEVICE"
echo ""

# Check if device exists
if ! flutter devices | grep -q "$DEVICE"; then
    echo "❌ Device $DEVICE not found!"
    echo ""
    echo "Available devices:"
    flutter devices
    exit 1
fi

echo "✅ Starting app on $DEVICE..."
flutter run -d "$DEVICE"

