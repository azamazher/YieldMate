# 📱 Complete Testing Guide: Live Detection on Mobile

This guide explains how to set up and test the Live Detection feature on your mobile device with a simple, single IP address configuration.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Finding Your Laptop's IP Address](#finding-your-laptops-ip-address)
3. [Configuring the Server URL](#configuring-the-server-url)
4. [Starting the Flask Server](#starting-the-flask-server)
5. [Testing Connection from Phone](#testing-connection-from-phone)
6. [Setting Up Live Detection](#setting-up-live-detection)
7. [Complete Testing Steps](#complete-testing-steps)
8. [Troubleshooting](#troubleshooting)

---

## ✅ Prerequisites

Before testing, ensure you have:

- ✅ Flask server dependencies installed (`requirements.txt`)
- ✅ Flutter app dependencies installed (`flutter pub get`)
- ✅ Both devices on the **same Wi-Fi network**
- ✅ Flask server running on port 5000
- ✅ Mobile device with camera permissions granted

---

## 🔍 Finding Your Laptop's IP Address

### Step 1: Connect Both Devices to Same Network

1. **Laptop**: Connect to Wi-Fi network
2. **Mobile Phone**: Connect to the **same** Wi-Fi network
3. **Important**: Both must be on the same network (not mobile data)

### Step 2: Find Your Laptop's IP Address

#### On macOS/Linux:

```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Example output:**
```
inet 172.20.10.3 netmask 0xfffffff0 broadcast 172.20.10.15
```

Your IP address is: **`172.20.10.3`**

#### Alternative (macOS only):

```bash
ipconfig getifaddr en0
```

This directly returns your IP: `172.20.10.3`

#### On Windows:

```cmd
ipconfig
```

Look for **IPv4 Address** under your active network adapter:
```
IPv4 Address. . . . . . . . . . . : 192.168.1.100
```

Your IP address is: **`192.168.1.100`**

---

## ⚙️ Configuring the Server URL

### Update the Server URL in Code

Open `lib/frontend/services/backend_service.dart` and update the IP address:

**For Android Physical Device:**
```dart
} else if (Platform.isAndroid) {
  return 'http://172.20.10.3:5000'; // Replace 172.20.10.3 with YOUR IP
}
```

**For iOS Physical Device:**
```dart
} else if (Platform.isIOS) {
  return 'http://172.20.10.3:5000'; // Replace 172.20.10.3 with YOUR IP
}
```

**Example:** If your IP is `192.168.1.100`, use:
```dart
return 'http://192.168.1.100:5000';
```

### Important Notes:

- **Update when IP changes**: If you connect to a different Wi-Fi network, your IP will change. Update the code with the new IP.
- **Emulator vs Physical Device**: 
  - **Android Emulator**: Use `http://10.0.2.2:5000`
  - **Physical Device**: Use your laptop's IP (e.g., `http://172.20.10.3:5000`)

---

## 🚀 Starting the Flask Server

### Step 1: Navigate to Project Directory

```bash
cd /Users/aazamazher/Development/projects/Fruit-Detection
```

### Step 2: Start the Server

```bash
python3 lib/backend/backend_server_example.py
```

### Step 3: Verify Server is Running

You should see output like:
```
💻 Running in local development environment
✅ Using model: /path/to/model.tflite
✅ Loaded 8 class names from labels.txt
Starting fruit detection server...
Server will run on http://0.0.0.0:5000
Debug mode: True
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://172.20.10.3:5000
```

**Note the IP address shown** - this should match your laptop's IP!

---

## 📱 Testing Connection from Phone

### Step 1: Test Server Health Endpoint

On your phone, open a web browser (Chrome, Safari, etc.) and go to:

```
http://172.20.10.3:5000/health
```

**Replace `172.20.10.3` with your actual IP address!**

### Step 2: Expected Response

You should see:
```json
{"status": "ok", "model": "loaded"}
```

### Step 3: If It Doesn't Work

If you see "Page not found" or timeout:

1. **Check firewall**: macOS Firewall might be blocking
   - System Settings → Network → Firewall → Options
   - Allow incoming connections for Python

2. **Check IP address**: Make sure you're using the correct IP
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

3. **Check network**: Both devices must be on same Wi-Fi

4. **Check server**: Make sure Flask server is still running

---

## 🎥 Setting Up Live Detection

### Step 1: Update Server URL in Code

1. Open: `lib/frontend/services/backend_service.dart`
2. Find line ~18-19 (Android) or ~21-22 (iOS)
3. Replace IP address with your laptop's IP:
   ```dart
   return 'http://172.20.10.3:5000'; // Your IP here
   ```

### Step 2: Install Dependencies

```bash
# Flutter dependencies
flutter pub get

# Python dependencies (if not already installed)
pip3 install -r requirements.txt
```

### Step 3: Build and Install App

```bash
# For Android
flutter run

# Or build APK
flutter build apk
```

---

## ✅ Complete Testing Steps

### Test 1: Server Connection

1. ✅ Start Flask server on laptop
2. ✅ Check server output shows your IP (e.g., `Running on http://172.20.10.3:5000`)
3. ✅ Test from phone browser: `http://172.20.10.3:5000/health`
4. ✅ Should see: `{"status": "ok", "model": "loaded"}`

### Test 2: App Connection

1. ✅ Open the app on your phone
2. ✅ Go to Live Detection page
3. ✅ Check Server Info button (top-right)
4. ✅ Should show: "Connected ✅" and server URL

### Test 3: Camera Access

1. ✅ Open Live Detection
2. ✅ Grant camera permissions if prompted
3. ✅ Should see camera preview

### Test 4: Detection Functionality

1. ✅ Point camera at fruits
2. ✅ Wait a few seconds for detection
3. ✅ Should see:
   - Green bounding boxes around fruits
   - Fruit name and ID labels (e.g., "apple #0")
   - Total count increasing
   - Active objects count

### Test 5: Tracking and Counting

1. ✅ Point camera at a fruit
2. ✅ Keep it in view - bounding box should stay stable
3. ✅ Move camera - box should follow smoothly
4. ✅ Add more fruits - count should increment
5. ✅ Same fruit shouldn't be counted twice

### Test 6: Controls

1. ✅ Pause button - should pause detection
2. ✅ Resume button - should resume detection
3. ✅ Reset button - should reset counter to 0
4. ✅ Server Info button - should show server details

---

## 🔧 How We Found the IP and Connected

### Our Testing Process:

1. **Found Laptop IP**:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   # Result: 172.20.10.3
   ```

2. **Updated Code**:
   - Changed `lib/frontend/services/backend_service.dart`
   - Set server URL to: `http://172.20.10.3:5000`

3. **Tested from Phone Browser**:
   - Opened: `http://172.20.10.3:5000/health`
   - Got response: `{"status": "ok", "model": "loaded"}`
   - ✅ Connection works!

4. **Ran App on Phone**:
   - App connected to server automatically
   - Live detection started working
   - Fruits detected and counted correctly

### Key Points:

- **Same Network**: Both laptop and phone connected to same Wi-Fi
- **Correct IP**: Used laptop's IP address (172.20.10.3)
- **Server Running**: Flask server was active on port 5000
- **Firewall Allowed**: Python allowed through macOS Firewall

---

## 🐛 Troubleshooting

### Issue: "Page not found" in browser

**Solutions:**
1. Check Flask server is running
2. Verify IP address is correct
3. Check firewall settings
4. Ensure both devices on same network

### Issue: App shows "Connection timeout"

**Solutions:**
1. Verify IP in `backend_service.dart` matches laptop IP
2. Test from browser first
3. Check server logs for incoming requests
4. Restart Flask server

### Issue: Camera not working

**Solutions:**
1. Grant camera permissions
2. Check device has camera
3. Restart the app
4. Check logs for camera errors

### Issue: No detections appearing

**Solutions:**
1. Check server is processing requests (check Flask logs)
2. Ensure fruits are clearly visible
3. Check lighting conditions
4. Verify model file exists (`assets/model.tflite`)

### Issue: IP Address Changed

**If you connect to a different Wi-Fi:**
1. Find new IP: `ifconfig | grep "inet " | grep -v 127.0.0.1`
2. Update `backend_service.dart` with new IP
3. Hot restart app: `r` in Flutter terminal
4. Test connection again

---

## 📝 Quick Reference

### Find IP Address:
```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# macOS (direct)
ipconfig getifaddr en0

# Windows
ipconfig
```

### Update Server URL:
**File**: `lib/frontend/services/backend_service.dart`  
**Line**: ~18-19 (Android) or ~21-22 (iOS)  
**Change**: `http://YOUR_IP_HERE:5000`

### Start Server:
```bash
python3 lib/backend/backend_server_example.py
```

### Test Connection:
```
http://YOUR_IP:5000/health
```

### Expected Response:
```json
{"status": "ok", "model": "loaded"}
```

---

## 🎯 Testing Checklist

Use this checklist when testing:

- [ ] Laptop and phone on same Wi-Fi network
- [ ] Found laptop's IP address
- [ ] Updated server URL in `backend_service.dart`
- [ ] Flask server running successfully
- [ ] Browser test works (`/health` endpoint)
- [ ] App installed on phone
- [ ] Camera permissions granted
- [ ] Live Detection page opens
- [ ] Server Info shows "Connected ✅"
- [ ] Camera preview visible
- [ ] Fruits detected with bounding boxes
- [ ] Counting works correctly
- [ ] No duplicate counting
- [ ] Bounding boxes stay stable
- [ ] Pause/Resume works
- [ ] Reset counter works

---

## 📸 What Success Looks Like

### Server Terminal:
```
✅ Using model: /path/to/model.tflite
✅ Loaded 8 class names
Starting fruit detection server...
Server will run on http://0.0.0.0:5000
 * Running on http://172.20.10.3:5000
```

### Phone Browser Test:
```
http://172.20.10.3:5000/health
→ {"status": "ok", "model": "loaded"}
```

### App Screen:
- Camera preview showing
- Green bounding boxes around fruits
- Total count: X
- Status: "Active" (green dot)
- Server Info shows: "Connected ✅"

---

## 🎉 You're Ready!

Once all checks pass, your live detection is fully working! Point your camera at fruits and watch them get detected and counted in real-time.

**Happy Testing!** 🍎🍌🍊🍇

