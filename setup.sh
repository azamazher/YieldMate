#!/bin/bash

# Fix UTF-8 encoding issue
export LANG=en_US.UTF-8

echo "Setting up Fruit Detection project..."
echo ""

# Navigate to project directory
cd "$(dirname "$0")"

echo "Installing Flutter dependencies..."
flutter pub get

echo ""
echo "Installing iOS CocoaPods..."
cd ios
pod install
cd ..

echo ""
echo "Installing macOS CocoaPods..."
cd macos
pod install
cd ..

echo ""
echo "Setup complete! You can now run:"
echo "flutter run"
echo ""

