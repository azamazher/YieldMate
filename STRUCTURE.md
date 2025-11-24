# YieldMate - Complete Project Structure & Code Documentation

This comprehensive document provides a complete overview of the project structure, code organization, and detailed information about what code is located in which file.

---

## 📁 Project Structure

```
Fruit-Detection/
├── lib/
│   ├── main.dart                    # Entry point (imports from frontend)
│   ├── frontend/                    # 🎨 ALL FRONTEND CODE (Flutter/Dart)
│   │   ├── app/
│   │   │   └── app.dart            # App configuration & theme
│   │   ├── models/
│   │   │   └── detection_record.dart
│   │   ├── pages/
│   │   │   ├── home_page.dart      # Main detection page
│   │   │   ├── calendar_page.dart
│   │   │   ├── fruit_doctor_page.dart
│   │   │   ├── community_page.dart
│   │   │   └── about_page.dart
│   │   ├── services/
│   │   │   ├── model_service.dart      # TFLite model operations
│   │   │   ├── detection_service.dart  # Post-processing, NMS
│   │   │   ├── backend_service.dart    # Backend API communication
│   │   │   └── storage_service.dart    # Local storage
│   │   └── widgets/
│   │       ├── splash_screen.dart
│   │       ├── pitchfork_icon_painter.dart
│   │       ├── bounding_box_painter.dart
│   │       ├── mode_toggle_button.dart
│   │       └── app_drawer.dart
│   │
│   └── backend/                     # 🖥️ ALL BACKEND CODE (Python)
│       ├── backend_server_example.py   # Flask server with Ultralytics
│       ├── start_server.sh             # Start backend server
│       └── stop_server.sh              # Stop backend server
│
├── assets/                          # Shared assets (model, labels)
│   ├── model.tflite
│   ├── labels.txt
│   └── icon/
│
├── scripts/                         # Development utilities
│   ├── add_image_android.sh
│   ├── add_images_to_emulator.sh
│   ├── run_android.sh
│   └── new.sh
│
├── test/                           # Tests
│   └── widget_test.dart
│
└── [other Flutter project files]
```

---

## 📄 File-by-File Documentation

### 🚀 Entry Point

#### `lib/main.dart`
**Purpose:** Application entry point  
**Lines:** ~11 lines  
**Contents:**
- `main()` function that initializes Flutter and runs the app
- Imports and runs `MyApp` from `frontend/app/app.dart`

**Key Code:**
```dart
void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}
```

---

### 🎨 Frontend Code (`lib/frontend/`)

#### `lib/frontend/app/app.dart`
**Purpose:** App-wide configuration, theme management, and routing  
**Lines:** ~79 lines  
**Contents:**
- `MyApp` widget - Root widget of the application
- `_MyAppState` - Manages theme mode (light/dark/system)
- Theme configuration (light and dark themes)
- Route definitions for all pages
- Navigation setup

**Key Classes:**
- `MyApp` - StatefulWidget for app configuration
- `_MyAppState` - Manages theme state and routes

**Routes:**
- `/` - SplashScreen
- `/home` - MyHomePage (main detection page)
- `/calendar` - CalendarPage
- `/fruit-doctor` - FruitDoctorPage
- `/community` - CommunityPage
- `/about` - AboutPage

---

#### `lib/frontend/pages/home_page.dart`
**Purpose:** Main fruit detection interface  
**Lines:** ~838 lines  
**Contents:**
- `MyHomePage` - Main detection page widget
- `AppState` enum - Tracks app state (initial, imageSelected, detecting, results)
- Image picking (camera/gallery)
- Model loading and inference
- Online/Offline mode switching
- Detection results display
- UI building methods for all screen states

**Key Classes:**
- `MyHomePage` - Main page widget
- `_MyHomePageState` - Manages detection state, model, and UI

**Key Methods:**
- `_loadModelAndLabels()` - Loads TFLite model and labels
- `_predictImage()` - Runs detection (offline or online)
- `_getImage()` - Picks image from camera/gallery
- `_buildInitialScreen()` - UI for no image selected
- `_buildImageSelectedScreen()` - UI for image ready to detect
- `_buildResultsScreen()` - UI for showing detection results
- `_buildGreenButton()` / `_buildGreyButton()` - Reusable button widgets

**State Variables:**
- `_appState` - Current app state
- `_image` - Selected image file
- `_recognitions` - Detection results
- `_interpreter` - TFLite model interpreter
- `_labels` - Class labels (fruit names)
- `_useOnlineMode` - Detection mode flag
- `_isOnline` - Internet connectivity status

---

#### `lib/frontend/pages/calendar_page.dart`
**Purpose:** Calendar view for detection history  
**Lines:** ~265 lines  
**Contents:**
- Displays past detections organized by date
- Shows fruit counts per day
- Uses `StorageService` to load detection records

---

#### `lib/frontend/pages/fruit_doctor_page.dart`
**Purpose:** Fruit information and tips  
**Lines:** ~69 lines  
**Contents:**
- Educational content about fruits
- Tips and recommendations

---

#### `lib/frontend/pages/community_page.dart`
**Purpose:** Community features  
**Lines:** ~69 lines  
**Contents:**
- Community-related functionality

---

#### `lib/frontend/pages/about_page.dart`
**Purpose:** About the app  
**Lines:** ~201 lines  
**Contents:**
- App information and credits

---

### 🎨 Widgets (`lib/frontend/widgets/`)

#### `lib/frontend/widgets/splash_screen.dart`
**Purpose:** Animated splash screen on app launch  
**Lines:** ~120 lines  
**Contents:**
- `SplashScreen` - Animated splash screen widget
- Logo animations (scale, rotation, fade)
- Navigation to home page after animation
- Theme mode initialization

**Key Classes:**
- `SplashScreen` - Splash screen widget
- `_SplashScreenState` - Manages animations

**Animations:**
- Scale animation (logo grows)
- Rotation animation (subtle rotation)
- Fade animation (text fades in)

---

#### `lib/frontend/widgets/pitchfork_icon_painter.dart`
**Purpose:** Custom drawn pitchfork icon  
**Lines:** ~60 lines  
**Contents:**
- `PitchforkIconPainter` - Custom painter for drawing icon
- Fallback icon if image asset is not found

**Key Classes:**
- `PitchforkIconPainter` - CustomPainter for icon

---

#### `lib/frontend/widgets/bounding_box_painter.dart`
**Purpose:** Draws bounding boxes and labels on detected images  
**Lines:** ~90 lines  
**Contents:**
- `BoundingBoxPainter` - Custom painter for detection visualization
- Draws bounding boxes with fruit-specific colors
- Displays class name and confidence percentage
- Scales boxes to match displayed image size

**Key Classes:**
- `BoundingBoxPainter` - CustomPainter for bounding boxes

**Features:**
- Color-coded boxes per fruit type
- Confidence score display
- Proper scaling for different image sizes

---

#### `lib/frontend/widgets/mode_toggle_button.dart`
**Purpose:** Toggle button for switching between offline/online detection modes  
**Lines:** ~80 lines  
**Contents:**
- `ModeToggleButton` - Glassmorphic toggle button widget
- Visual feedback for online/offline status
- Shows connectivity indicator

**Key Classes:**
- `ModeToggleButton` - StatelessWidget for mode toggle

**Features:**
- Glassmorphic design
- Color-coded (green for offline, blue for online)
- Shows WiFi-off icon when online but no internet

---

#### `lib/frontend/widgets/app_drawer.dart`
**Purpose:** Navigation drawer for app navigation  
**Contents:**
- Drawer menu with navigation options
- Links to all pages

---

### ⚙️ Services (`lib/frontend/services/`)

#### `lib/frontend/services/model_service.dart`
**Purpose:** TFLite model loading and inference operations  
**Lines:** ~258 lines  
**Contents:**
- `ModelService` - Static service class for model operations
- Model loading from assets
- Image preprocessing (resize, normalize)
- Model inference in isolates (background threads)
- Output format handling

**Key Classes:**
- `ModelService` - Static service class

**Key Methods:**
- `loadModelAndLabels()` - Loads model and labels from assets
- `runModelIsolate()` - Runs inference in isolate (static, for background processing)

**Features:**
- Handles model loading errors gracefully
- Supports multiple asset paths (fallback)
- Image preprocessing (resize to 640x640, normalize to [0,1])
- Runs inference in isolate to avoid blocking UI
- Handles different output tensor formats

---

#### `lib/frontend/services/detection_service.dart`
**Purpose:** Post-processing of model output (NMS, IoU, sigmoid)  
**Lines:** ~272 lines  
**Contents:**
- `DetectionService` - Static service class for post-processing
- Output format detection and transposition
- Sigmoid application for logits
- Confidence threshold filtering
- Non-Maximum Suppression (NMS)
- Intersection over Union (IoU) calculation

**Key Classes:**
- `DetectionService` - Static service class

**Key Methods:**
- `processOutput()` - Main post-processing function
- `nonMaxSuppression()` - Removes duplicate detections
- `calculateIoU()` - Calculates intersection over union

**Processing Steps:**
1. Validate output dimensions
2. Detect output format ([batch, classes+4, detections] or [batch, detections, classes+4])
3. Transpose if needed
4. Pre-filter by raw logit value (threshold: 0.3)
5. Apply sigmoid to convert logits to probabilities
6. Filter by confidence threshold (default: 0.5)
7. Convert xywh to xyxy bounding box format
8. Apply Non-Maximum Suppression (IoU threshold: 0.45)
9. Return final detections

**Key Parameters:**
- `confThreshold`: 0.5 (confidence threshold)
- `iouThreshold`: 0.45 (IoU threshold for NMS)
- `maxRawLogit`: 0.3 (pre-filter threshold before sigmoid)

---

#### `lib/frontend/services/backend_service.dart`
**Purpose:** Communication with Python backend server for online detection  
**Lines:** ~100 lines  
**Contents:**
- `BackendDetectionService` - Service for backend API calls
- HTTP requests to Flask server
- Server health checks
- Platform-specific URL detection (Android/iOS/Web)

**Key Classes:**
- `BackendDetectionService` - Service class for backend communication

**Key Methods:**
- `detectFruits()` - Sends image to backend for detection
- `checkHealth()` - Checks if backend server is reachable

**Platform URLs:**
- Android Emulator: `http://10.0.2.2:5000`
- iOS Simulator: `http://localhost:5000`
- Web: `http://localhost:5000`
- Physical devices: Requires computer's IP address

---

#### `lib/frontend/services/storage_service.dart`
**Purpose:** Local storage for detection records  
**Contents:**
- Saves detection history
- Retrieves past detections
- Used by calendar page

---

### 📊 Models (`lib/frontend/models/`)

#### `lib/frontend/models/detection_record.dart`
**Purpose:** Data model for detection records  
**Lines:** ~45 lines  
**Contents:**
- `DetectionRecord` - Model class for storing detection data
- Fields: date, fruitCounts, imagePath, timestamp

---

### 🖥️ Backend Code (`lib/backend/`)

#### `lib/backend/backend_server_example.py`
**Purpose:** Flask server with Ultralytics YOLO for online detection  
**Lines:** ~107 lines  
**Contents:**
- Flask REST API server
- Uses Ultralytics YOLO library
- Handles image uploads from Flutter app
- Returns detection results in JSON format

**Key Features:**
- Loads TFLite model using Ultralytics
- Reads class names from `assets/labels.txt`
- REST endpoints: `/detect` (POST), `/health` (GET)
- CORS enabled for Flutter app
- Automatic path resolution (finds model relative to project root)

**Endpoints:**
- `POST /detect` - Receives image, returns detections
- `GET /health` - Server health check

**Model Path Resolution:**
- Primary: `../../assets/model.tflite` (from `lib/backend/`)
- Fallback: `../../runs/multi_fruit_model/weights/best_saved_model/best_float32.tflite`

---

#### `lib/backend/start_server.sh`
**Purpose:** Start script for backend server  
**Contents:**
- Checks Python 3 availability
- Verifies dependencies (flask, ultralytics, pillow)
- Installs missing dependencies
- Checks port 5000 availability
- Starts Flask server
- Navigates to project root before running

**Usage:**
```bash
cd lib/backend
./start_server.sh
```

---

#### `lib/backend/stop_server.sh`
**Purpose:** Stop script for backend server  
**Contents:**
- Finds process on port 5000
- Kills the server process

**Usage:**
```bash
cd lib/backend
./stop_server.sh
```

---

## 🔄 Data Flow

### Offline Detection Flow:
1. User selects image → `home_page.dart` → `_getImage()`
2. User taps "Detect" → `_predictImage()`
3. Load model bytes → `model_service.dart` → `ModelService.loadModelAndLabels()`
4. Run inference in isolate → `model_service.dart` → `ModelService.runModelIsolate()`
5. Post-process output → `detection_service.dart` → `DetectionService.processOutput()`
6. Display results → `home_page.dart` → `_buildResultsScreen()`
7. Draw bounding boxes → `bounding_box_painter.dart` → `BoundingBoxPainter`

### Online Detection Flow:
1. User selects image → `home_page.dart` → `_getImage()`
2. User taps "Detect" → `_predictImage()`
3. Check server health → `backend_service.dart` → `BackendDetectionService.checkHealth()`
4. Send image to server → `backend_service.dart` → `BackendDetectionService.detectFruits()`
5. Backend processes with Ultralytics YOLO → `backend_server_example.py`
6. Receive results → `home_page.dart`
7. Display results → `home_page.dart` → `_buildResultsScreen()`

---

## 🎯 Key Concepts

### App States (`AppState` enum):
- `initial` - No image selected
- `imageSelected` - Image selected, ready to detect
- `detecting` - Detection in progress
- `results` - Detection complete, showing results

### Detection Modes:
- **Offline Mode**: Uses TFLite model on device
- **Online Mode**: Uses backend server with Ultralytics YOLO

### Model Output Format:
- Expected: `[1, 12, 8400]` or `[1, 8400, 12]`
- Format: `[batch, classes+4, detections]` or `[batch, detections, classes+4]`
- 12 = 8 classes + 4 bbox coordinates (cx, cy, w, h)
- 8400 = number of detection anchors

### Post-Processing Pipeline:
1. **Pre-filter**: Filter by raw logit value (< 0.3 = noise)
2. **Sigmoid**: Convert logits to probabilities
3. **Confidence Filter**: Keep detections with confidence > 0.5
4. **NMS**: Remove overlapping detections (IoU > 0.45)
5. **Scale**: Convert normalized coordinates to image coordinates

---

## 🔧 Configuration

### Model Configuration:
- **Input Size**: 640x640 pixels
- **Model Path**: `assets/model.tflite`
- **Labels Path**: `assets/labels.txt`
- **Classes**: 8 fruits (apple, watermelon, mango, strawberry, banana, orange, pineapple, grape)

### Detection Thresholds:
- **Confidence Threshold**: 0.5
- **IoU Threshold**: 0.45
- **Pre-filter Logit Threshold**: 0.3

### Backend Configuration:
- **Default Port**: 5000
- **Health Endpoint**: `/health`
- **Detection Endpoint**: `/detect`
- **Server URL**: Auto-detected based on platform

---

## 📝 Import Paths

### Main Entry Point:
```dart
// lib/main.dart
import 'frontend/app/app.dart';
```

### Frontend Files:
All relative imports within `frontend/` use relative paths:
```dart
// lib/frontend/pages/home_page.dart
import '../services/model_service.dart';
import '../widgets/bounding_box_painter.dart';
```

### Test Files:
```dart
// test/widget_test.dart
import 'package:fruits_detection/frontend/app/app.dart';
```

---

## 🚀 Running the Project

### Frontend (Flutter):
```bash
# From project root
flutter run
```

### Backend (Python):
```bash
# From project root
python3 lib/backend/backend_server_example.py

# Or use the script
cd lib/backend
./start_server.sh
```

### Development Scripts:
```bash
# Setup project
./setup.sh

# Run on Android
./scripts/run_android.sh

# Add test images to emulator
./scripts/add_image_android.sh <image_path>
```

---

## 🔄 Path Resolution

### Backend Server:
The backend server automatically resolves paths relative to the **project root**:
- Model: `../../assets/model.tflite` (from `lib/backend/`)
- Labels: `../../assets/labels.txt` (from `lib/backend/`)
- Fallback: `../../runs/multi_fruit_model/...` (from `lib/backend/`)

The server script (`start_server.sh`) changes to project root before running, so paths work correctly.

---

## ✅ Benefits of This Structure

1. **Everything in `lib/`**: Both frontend and backend code are under `lib/` for consistency
2. **Clear Separation**: Frontend (`lib/frontend/`) and backend (`lib/backend/`) are clearly separated
3. **Easy Navigation**: Know exactly where to find frontend vs backend code
4. **Better Organization**: Related code is grouped together
5. **Scalability**: Easy to add more frontend or backend components
6. **Maintainability**: Easier to understand project structure
7. **Modular Design**: Services, widgets, and pages are separated for easy maintenance

---

## 🐛 Troubleshooting

### Model Loading Issues:
- Check if `assets/model.tflite` exists
- Verify `assets/labels.txt` is present
- Check platform compatibility (macOS has limited support)

### Backend Connection Issues:
- Verify server is running on port 5000
- Check URL for your platform (emulator vs physical device)
- Ensure firewall allows connections
- Check if server can find model at `../../assets/model.tflite`

### Detection Issues:
- Check confidence threshold (may need adjustment)
- Verify model output format matches expected format
- Check logs for post-processing errors
- Ensure model is properly loaded before detection

---

## 📚 Additional Resources

- **TFLite Documentation**: https://www.tensorflow.org/lite
- **Ultralytics YOLO**: https://docs.ultralytics.com
- **Flutter Documentation**: https://flutter.dev/docs

---

## 📋 Scripts Documentation

### Development Scripts (`scripts/`):
- **`add_image_android.sh`** - Add a single image to Android emulator
- **`add_images_to_emulator.sh`** - Add images to Android emulator gallery
- **`run_android.sh`** - Run Flutter app on Android emulator
- **`new.sh`** - Clean and run Flutter app on macOS

### Setup Scripts:
- **`setup.sh`** - Project setup (installs dependencies, CocoaPods)

### Backend Scripts:
- **`lib/backend/start_server.sh`** - Start Flask backend server
- **`lib/backend/stop_server.sh`** - Stop Flask backend server

---

*Last Updated: After complete reorganization and documentation merge*
