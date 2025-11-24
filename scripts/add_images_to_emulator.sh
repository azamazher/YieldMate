#!/bin/bash

# Script to add images to Android emulator gallery for testing
# Usage: ./add_images_to_emulator.sh <path_to_image_file>

echo "📱 Adding images to Android emulator gallery..."
echo ""

# Find adb in Android SDK
ANDROID_SDK="$HOME/Library/Android/sdk"
ADB_PATH="$ANDROID_SDK/platform-tools/adb"

if [ ! -f "$ADB_PATH" ]; then
    echo "❌ ADB not found at $ADB_PATH"
    echo "Please ensure Android SDK is installed and update the ADB_PATH in this script"
    exit 1
fi

# Check if emulator is running
DEVICES=$($ADB_PATH devices | grep -v "List" | grep "device" | wc -l | tr -d ' ')
if [ "$DEVICES" -eq 0 ]; then
    echo "❌ No Android devices/emulators found!"
    echo "Please start an Android emulator first"
    exit 1
fi

echo "✅ Found Android device/emulator"
echo ""

# Check if image file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_image_file>"
    echo ""
    echo "Example:"
    echo "  $0 ~/Pictures/fruit.jpg"
    echo "  $0 ./test_images/apple.png"
    echo ""
    echo "To add multiple images:"
    echo "  for img in ~/Pictures/*.jpg; do $0 \"\$img\"; done"
    exit 1
fi

IMAGE_FILE="$1"

if [ ! -f "$IMAGE_FILE" ]; then
    echo "❌ Image file not found: $IMAGE_FILE"
    exit 1
fi

# Get the filename
FILENAME=$(basename "$IMAGE_FILE")

# Push image to Pictures directory (Android 10+ uses scoped storage)
echo "📤 Pushing $FILENAME to emulator..."
$ADB_PATH push "$IMAGE_FILE" /sdcard/Pictures/

if [ $? -eq 0 ]; then
    echo "✅ Image added successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Open the Gallery app on your emulator"
    echo "2. The image should appear in the Pictures folder"
    echo "3. Or use the 'Choose from Gallery' button in your app"
else
    echo "❌ Failed to add image. Trying alternative method..."
    
    # Alternative: Try Downloads folder
    $ADB_PATH push "$IMAGE_FILE" /sdcard/Download/
    if [ $? -eq 0 ]; then
        echo "✅ Image added to Downloads folder!"
    else
        echo "❌ Failed to add image. Please check:"
        echo "   - Emulator is running and unlocked"
        echo "   - File permissions"
        echo "   - ADB connection"
    fi
fi

