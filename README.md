# YieldMate - Smart Fruit Detection App

A Flutter mobile application for detecting fruits in images using AI and YOLOv8 model. Supports both offline (TFLite) and online (backend server) detection modes.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Flutter SDK** (>=3.4.3) - [Install Flutter](https://flutter.dev/docs/get-started/install)
- **Dart SDK** (comes with Flutter)
- **Python 3** - [Install Python](https://www.python.org/downloads/)
- **Android Studio** or **Xcode** (for mobile development)
- **Git** - [Install Git](https://git-scm.com/downloads)

## 🚀 Getting Started

### Step 1: Clone the Repository

```bash
git clone <your-repository-url>
cd Fruit-Detection
```

### Step 2: Install Flutter Dependencies

```bash
flutter pub get
```

This will install all Flutter/Dart packages defined in `pubspec.yaml`.

### Step 3: Install Platform-Specific Dependencies

#### For iOS (macOS only):
```bash
cd ios
pod install
cd ..
```

#### For macOS:
```bash
cd macos
pod install
cd ..
```

**Or use the setup script:**
```bash
./setup.sh
```

This script automatically runs `flutter pub get` and installs CocoaPods for iOS/macOS.

### Step 4: Install Backend Dependencies (for Online Mode)

The backend server requires Python packages:

```bash
pip3 install flask flask-cors ultralytics pillow
```

**Note:** The server start script will automatically install these if missing.

### Step 5: Verify Assets

Ensure the following files exist in the `assets/` folder:
- `assets/model.tflite` - The trained YOLOv8 model
- `assets/labels.txt` - Class labels (fruit names)
- `assets/icon/splash_icon.png` - App icon (optional)

**Important:** These files are **NOT** included in the repository (see `.gitignore`). You need to:
1. Train your own model, or
2. Obtain the model files from the project maintainer

### Step 6: Run the Application

#### Option A: Using Flutter CLI
```bash
flutter run
```

#### Option B: Using Android Studio / VS Code
- Open the project in your IDE
- Select a device/emulator
- Click the Run button

## 🖥️ Running the Backend Server (for Online Mode)

The backend server is required for online detection mode. It uses Ultralytics YOLO to process images.

### Start the Server

```bash
./lib/backend/start_server.sh
```

**Or manually:**
```bash
python3 lib/backend/backend_server_example.py
```

The server will:
- Start on `http://localhost:5000`
- Automatically check and install Python dependencies
- Load the model from `assets/model.tflite`
- Provide endpoints:
  - `GET /health` - Health check
  - `POST /detect` - Fruit detection

### Stop the Server

Press `Ctrl+C` in the terminal, or:

```bash
./lib/backend/stop_server.sh
```

## 📱 App Modes

### Offline Mode (Default)
- Uses TFLite model on device
- No internet connection required
- Works completely offline

### Online Mode
- Uses backend server with Ultralytics YOLO
- Requires backend server to be running
- Requires internet connection (or local network access)

**Toggle between modes:** Use the mode toggle button in the app interface.

## 📁 Project Structure

```
Fruit-Detection/
├── lib/
│   ├── main.dart                    # Entry point
│   ├── frontend/                    # Flutter/Dart code
│   │   ├── app/                     # App configuration
│   │   ├── pages/                   # UI pages
│   │   ├── services/                # Business logic
│   │   ├── widgets/                 # UI components
│   │   └── models/                  # Data models
│   └── backend/                     # Python server
│       ├── backend_server_example.py
│       ├── start_server.sh
│       └── stop_server.sh
├── assets/                          # Model & labels (not in git)
├── scripts/                         # Development utilities
└── test/                           # Tests
```

For detailed structure, see [STRUCTURE.md](STRUCTURE.md).

## ⚠️ Important: Files Not in Git (.gitignore)

The following files/folders are **NOT** included in the repository:

### Build Artifacts (Auto-generated):
- `build/` - Build outputs
- `.dart_tool/` - Dart tooling cache
- `.pub/` - Pub cache
- `android/app/debug/`, `android/app/release/` - Android builds
- `ios/Pods/` - iOS dependencies (run `pod install`)
- `macos/Pods/` - macOS dependencies (run `pod install`)

### IDE Files:
- `.idea/` - IntelliJ/Android Studio settings
- `*.iml` - IntelliJ module files
- `.vscode/` - VS Code settings (optional)

### Model Files (You Need to Provide):
- `assets/model.tflite` - **Required** - The trained model
- `assets/labels.txt` - **Required** - Class labels
- `assets/icon/splash_icon.png` - Optional - App icon

### Python Cache:
- `*.pyc` - Python bytecode
- `__pycache__/` - Python cache

**What You Need to Do:**
1. **Model Files**: Add your `model.tflite` and `labels.txt` to the `assets/` folder
2. **Dependencies**: Run `flutter pub get` and `pod install` (for iOS/macOS)
3. **Backend Dependencies**: Run `pip3 install flask flask-cors ultralytics pillow`

## 🔧 Troubleshooting

### Flutter Issues

**Problem:** `flutter pub get` fails
- **Solution:** Ensure Flutter SDK is properly installed and in PATH
- Run `flutter doctor` to check setup

**Problem:** iOS/macOS build fails
- **Solution:** Run `cd ios && pod install` or `cd macos && pod install`
- Ensure CocoaPods is installed: `sudo gem install cocoapods`

**Problem:** Model not found error
- **Solution:** Ensure `assets/model.tflite` exists in the project root
- Check `pubspec.yaml` includes the assets folder

### Backend Server Issues

**Problem:** Server won't start
- **Solution:** Check Python 3 is installed: `python3 --version`
- Install dependencies: `pip3 install flask flask-cors ultralytics pillow`
- Check port 5000 is not in use: `lsof -ti:5000`

**Problem:** Model not found (backend)
- **Solution:** Ensure `assets/model.tflite` exists in project root
- Server looks for model at: `../../assets/model.tflite` (from `lib/backend/`)

**Problem:** Can't connect to server from app
- **Solution:** 
  - For Android Emulator: Use `http://10.0.2.2:5000`
  - For iOS Simulator: Use `http://localhost:5000`
  - For Physical Devices: Use your computer's IP address (e.g., `http://192.168.1.XXX:5000`)

### Platform-Specific Issues

**Android:**
- Ensure Android SDK is installed
- Enable USB debugging for physical devices
- Use Android Studio to set up emulator

**iOS (macOS only):**
- Ensure Xcode is installed
- Run `pod install` in `ios/` directory
- For physical devices: Configure signing in Xcode

## 📚 Documentation

- [STRUCTURE.md](STRUCTURE.md) - Complete project structure and code documentation
- [scripts/README.md](scripts/README.md) - Development scripts documentation

## 🛠️ Development Scripts

Located in `scripts/` folder:
- `add_image_android.sh` - Add test images to Android emulator
- `run_android.sh` - Run app on Android emulator
- `new.sh` - Clean and run on macOS

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]

---

**Note:** This project requires the trained model file (`assets/model.tflite`) which is not included in the repository. Contact the project maintainer to obtain the model file.
