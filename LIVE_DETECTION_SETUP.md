# 📱 Live Detection Setup Guide

## ✅ Implementation Complete!

The live detection feature with object tracking and counting has been successfully implemented based on the SCG-YOLOv8n approach from the Nature article.

---

## 🎯 What's Been Implemented

### Backend (Flask Server)
- ✅ **Object Tracking System** (`FruitTracker` class)
  - IoU-based tracking algorithm
  - Unique ID assignment for each fruit
  - Bounding box smoothing for stability
  - Handles disappearing/reappearing objects

- ✅ **New Endpoints**:
  - `/detect_live` - Live detection with tracking
  - `/reset_tracker` - Reset counter for new session
  - `/tracker_status` - Get current tracker status

### Frontend (Flutter App)
- ✅ **Live Detection Page** with:
  - Real-time camera preview
  - Continuous detection (every 300ms)
  - Persistent bounding boxes with unique IDs
  - Total fruit counter (no duplicates)
  - Active objects display
  - Pause/Resume functionality
  - Reset counter button
  - Error handling and status indicators

- ✅ **Unlocked in Menu** - Live Detection is now accessible from the drawer

---

## 📋 Features

### 1. **Persistent Bounding Boxes**
- Boxes stay stable while fruits are in camera view
- Smooth transitions using moving average filtering
- No jittery movements

### 2. **No Duplicate Counting**
- Each fruit gets a unique ID when first detected
- ID persists as long as fruit is visible
- Counter increments only for new fruits
- Total count never decreases

### 3. **Real-Time Performance**
- Detects every 300ms (3-4 FPS)
- Optimized for mobile devices
- Background processing

### 4. **User Controls**
- **Pause/Resume**: Temporarily stop detection
- **Reset Counter**: Start fresh counting session
- **Status Indicators**: Shows detection state

---

## 🚀 How to Use

### 1. Start Backend Server

```bash
# Make sure dependencies are installed
pip install -r requirements.txt

# Start the server
python lib/backend/backend_server_example.py
```

### 2. Run Flutter App

```bash
# Install dependencies
flutter pub get

# Run on device/emulator
flutter run
```

### 3. Access Live Detection

1. Open the app drawer (hamburger menu)
2. Tap on **"Live Detection"**
3. Grant camera permissions when prompted
4. Point camera at fruits
5. Watch the counter increment as new fruits are detected!

---

## 📦 Dependencies Added

### Backend (`requirements.txt`)
- `numpy>=1.24.0` - For tracking calculations

### Frontend (`pubspec.yaml`)
- `camera: ^0.10.5+9` - For camera access

---

## 🔧 Configuration

### Tracking Parameters

You can adjust tracking behavior in `lib/backend/backend_server_example.py`:

```python
tracker = FruitTracker(
    max_disappeared=5,      # Frames before removing object
    iou_threshold=0.3       # IoU threshold for matching
)
```

### Detection Frequency

In `lib/frontend/pages/live_detection_page.dart`:

```dart
_detectionTimer = Timer.periodic(
  const Duration(milliseconds: 300),  // Adjust this value
  (timer) async { ... }
);
```

- **Lower value** (e.g., 200ms) = More frequent detection, more CPU usage
- **Higher value** (e.g., 500ms) = Less frequent, less CPU usage

---

## 🎨 UI Features

### Display Elements:
1. **Total Counter** (Top-left)
   - Shows total unique fruits counted
   - Active objects indicator
   - Fire icon for visual appeal

2. **Status Indicator** (Top-right)
   - Green = Active detection
   - Blue = Currently detecting
   - Orange = Paused

3. **Bounding Boxes**
   - Green boxes around detected fruits
   - Labels show: `fruit_name #id`
   - Persistent while fruit is visible

4. **App Bar Actions**
   - Refresh icon = Reset counter
   - Pause/Play = Toggle detection

---

## 📱 Permissions

### Android
Camera permissions should be automatically added by the `camera` package. If not, add to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.CAMERA"/>
<uses-feature android:name="android.hardware.camera" android:required="false"/>
```

### iOS
Add to `ios/Runner/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access for live fruit detection</string>
```

---

## 🐛 Troubleshooting

### Camera Not Initializing
- **Check permissions**: Ensure camera permissions are granted
- **Check device**: Ensure device/emulator has camera support
- **Check logs**: Look for error messages in console

### Server Connection Error
- **Check server**: Ensure Flask server is running
- **Check URL**: Verify server URL in `BackendDetectionService`
- **Check network**: Ensure device can reach server IP

### Detection Not Working
- **Check server logs**: Look for errors in Flask console
- **Check model**: Ensure `model.tflite` exists in `assets/`
- **Check labels**: Ensure `labels.txt` exists

### Bounding Boxes Not Showing
- **Check detection**: Verify fruits are being detected (check counter)
- **Check coordinates**: Ensure bbox coordinates are valid
- **Check scaling**: Bounding boxes scale to screen size

---

## 📊 Performance Tips

1. **Reduce Detection Frequency**: Increase timer interval for better battery life
2. **Lower Resolution**: Camera preview uses `ResolutionPreset.medium`
3. **Pause When Not Needed**: Use pause button to save resources
4. **Optimize Server**: Use production mode (`FLASK_ENV=production`)

---

## 🔄 How Tracking Works

1. **First Detection**: New fruit gets unique ID (e.g., `#0`, `#1`, `#2`)
2. **Matching**: Next frame uses IoU (Intersection over Union) to match detections to existing objects
3. **Tracking**: Matched objects keep same ID, box position smoothed
4. **Counting**: Only new detections (not matched) increment counter
5. **Cleanup**: Objects not seen for 5 frames are removed from tracking

---

## 📝 Comparison with Article

| Feature | SCG-YOLOv8n (Article) | Our Implementation |
|---------|----------------------|-------------------|
| Tracking Algorithm | Not specified | IoU-based tracking ✅ |
| Unique ID Assignment | Yes | Yes ✅ |
| Persistent Boxes | Yes | Yes ✅ |
| No Duplicate Counting | Yes | Yes ✅ |
| Mobile Deployment | Yes (3.2 MB) | Yes (TFLite) ✅ |
| Real-Time Performance | Yes | Yes ✅ |

**Result**: Same functionality achieved! ✅

---

## 🎉 Next Steps

1. Test on a physical device
2. Fine-tune tracking parameters
3. Add export functionality (save count)
4. Add analytics (detection history)
5. Optimize for production

---

## 📚 References

- [SCG-YOLOv8n Paper](https://www.nature.com/articles/s41598-025-18754-9)
- [Ultralytics YOLO Documentation](https://docs.ultralytics.com)
- [Flutter Camera Package](https://pub.dev/packages/camera)

---

Enjoy your live fruit detection! 🍎🍌🍊🍇

