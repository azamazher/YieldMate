# Development Scripts

This folder contains utility scripts for development and testing.

## Available Scripts

### Android Development

- **`add_image_android.sh`** - Add a single image to Android emulator for testing
  ```bash
  ./scripts/add_image_android.sh <image_path> [device_id]
  ```

- **`add_images_to_emulator.sh`** - Add images to Android emulator gallery
  ```bash
  ./scripts/add_images_to_emulator.sh <path_to_image_file>
  ```

- **`run_android.sh`** - Run Flutter app on Android emulator
  ```bash
  ./scripts/run_android.sh [device_id]
  ```

### macOS Development

- **`new.sh`** - Clean and run Flutter app on macOS
  ```bash
  ./scripts/new.sh
  ```

## Setup Script

The `setup.sh` script remains in the project root for easy access:
```bash
./setup.sh
```

## Backend Scripts

Backend server scripts are located in `lib/backend/`:
- `lib/backend/start_server.sh` - Start the Flask backend server
- `lib/backend/stop_server.sh` - Stop the Flask backend server

