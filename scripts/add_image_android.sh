#!/bin/bash

# Quick script to add images to Android emulator for testing
# Usage: ./add_image_android.sh <image_path> [device_id]

ADB="$HOME/Library/Android/sdk/platform-tools/adb"

if [ -z "$1" ]; then
    echo "📱 Add Image to Android Emulator"
    echo ""
    echo "Usage: $0 <image_path> [device_id]"
    echo ""
    echo "Examples:"
    echo "  $0 ~/Pictures/fruit.jpg"
    echo "  $0 ~/Pictures/fruit.jpg emulator-5554"
    echo ""
    echo "Available devices:"
    $ADB devices | grep -v "List"
    exit 1
fi

IMAGE_PATH="$1"
DEVICE="${2:-emulator-5554}"

if [ ! -f "$IMAGE_PATH" ]; then
    echo "❌ Image not found: $IMAGE_PATH"
    exit 1
fi

FILENAME=$(basename "$IMAGE_PATH")
echo "📤 Adding $FILENAME to $DEVICE..."

# Try multiple locations where Gallery apps look for images
LOCATIONS=(
    "/sdcard/Pictures/$FILENAME"
    "/sdcard/DCIM/Camera/$FILENAME"
    "/sdcard/Download/$FILENAME"
)

for LOCATION in "${LOCATIONS[@]}"; do
    echo "   Trying: $LOCATION"
    if $ADB -s "$DEVICE" push "$IMAGE_PATH" "$LOCATION" 2>/dev/null; then
        echo "✅ Successfully added to $LOCATION"
        
        # Trigger media scan so Gallery picks it up
        $ADB -s "$DEVICE" shell "am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://$LOCATION" >/dev/null 2>&1
        
        echo ""
        echo "🎉 Image added! It should appear in Gallery now."
        echo "💡 If it doesn't show up immediately:"
        echo "   1. Open Gallery app and pull down to refresh"
        echo "   2. Or restart the Gallery app"
        exit 0
    fi
done

echo "❌ Failed to add image. Make sure:"
echo "   - Emulator is running and unlocked"
echo "   - Device ID is correct: $DEVICE"
exit 1

