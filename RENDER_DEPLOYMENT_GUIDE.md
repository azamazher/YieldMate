# 🚀 Render Deployment Guide for Live Detection

**Complete step-by-step guide to deploy your Fruit Detection Flask server to Render for live detection functionality.**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [Post-Deployment Configuration](#post-deployment-configuration)
5. [Update Flutter App for Live Detection](#update-flutter-app-for-live-detection)
6. [Testing Live Detection](#testing-live-detection)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

---

## ✅ Prerequisites

Before you begin, ensure you have:

- ✅ **GitHub Account**: Free account is fine
- ✅ **Git Repository**: Your `Fruit-Detection` project pushed to GitHub
- ✅ **Model Files**: `assets/model.tflite` and `assets/labels.txt` must be in your repository
- ✅ **Render Account**: Sign up at [render.com](https://render.com) (free tier is sufficient)
- ✅ **Dockerfile**: The updated `Dockerfile` in your project root

### Verify Your Repository Structure

Your GitHub repository should have this structure:
```
Fruit-Detection/
├── Dockerfile                    ← Must be in root
├── requirements.txt
├── lib/
│   └── backend/
│       └── backend_server_example.py
└── assets/
    ├── model.tflite              ← Required for detection
    └── labels.txt                ← Required for detection
```

**⚠️ Important**: Make sure `model.tflite` and `labels.txt` are committed to Git. They are large files, but they're essential for the server to work.

---

## 📝 Pre-Deployment Checklist

Before deploying, complete these checks:

- [ ] All code is committed and pushed to GitHub
- [ ] `model.tflite` and `labels.txt` are in the repository (check file size > 0)
- [ ] `Dockerfile` is in the project root directory
- [ ] `requirements.txt` includes all dependencies
- [ ] Flask server runs locally and responds to `/health` endpoint
- [ ] You've tested the `/detect_live` endpoint locally (if possible)

### Test Locally with Docker First

```bash
# Navigate to your project directory
cd /Users/aazamazher/Development/projects/Fruit-Detection

# Build the Docker image
docker build -t fruit-detection-test .

# Run the container
docker run -d -p 5000:5000 --name fruit-test fruit-detection-test

# Test the health endpoint
curl http://localhost:5000/health

# Expected response:
# {"status": "ok", "model": "loaded"}

# Test live detection endpoint (requires image file)
curl -X POST http://localhost:5000/detect_live \
  -F "image=@/path/to/test/image.jpg" \
  -F "reset=false"

# Stop and remove test container
docker stop fruit-test && docker rm fruit-test
```

---

## 🚀 Step-by-Step Deployment

### Step 1: Create Render Account

1. Go to [render.com](https://render.com)
2. Click **"Get Started for Free"**
3. Choose **"Sign up with GitHub"** (recommended for easier repository access)
4. Authorize Render to access your GitHub repositories
5. Complete the account setup

### Step 2: Create New Web Service

1. In your Render dashboard, click **"New +"** button (top right)
2. Select **"Web Service"** from the dropdown menu

### Step 3: Connect Your Repository

1. **Connect Repository**:
   - If you signed up with GitHub, your repositories should appear automatically
   - If not, click **"Connect account"** and authorize Render
   - Find and select your `Fruit-Detection` repository
   
2. **Select Branch**:
   - Choose `main` or `master` (whichever branch has your latest code)
   - You can change this later if needed

3. Click **"Connect"**

### Step 4: Configure Service Settings

Fill in the following configuration:

#### Basic Settings

- **Name**: `fruit-detection-api` (or any name you prefer)
  - This will be part of your URL: `https://fruit-detection-api.onrender.com`
  
- **Region**: Choose the region closest to your users
  - **US East (Ohio)**: Best for US East Coast
  - **US West (Oregon)**: Best for US West Coast
  - **EU (Ireland)**: Best for Europe
  - **Asia Pacific (Singapore)**: Best for Asia
  
- **Branch**: `main` (or your default branch)

- **Root Directory**: Leave **empty** (uses repository root)
  - If your Dockerfile is in a subdirectory, specify it here (e.g., `./backend`)

#### Build & Deploy Settings

- **Environment**: Select **"Docker"**
  - This tells Render to use your Dockerfile
  
- **Dockerfile Path**: `Dockerfile`
  - Render will auto-detect this, but you can specify it explicitly
  
- **Docker Context**: `.` (dot means root directory)
  - Only needed if Dockerfile is in a subdirectory

#### Instance Type

- **Plan**: Select **"Free"** 
  - **Note**: Free tier sleeps after 15 minutes of inactivity
  - First request after sleep takes ~30-60 seconds to wake up
  - For always-on service, upgrade to **"Starter"** ($7/month)

#### Advanced Settings (Click "Advanced" to expand)

**Health Check Path**: `/health`
- This endpoint tells Render if your service is healthy

**Auto-Deploy**: `Yes` (default)
- Automatically deploys when you push to the selected branch

**Deploy Hooks**: Leave empty (optional)
- Can add pre/post deploy scripts if needed

### Step 5: Environment Variables

Click **"Advanced"** → **"Environment Variables"** and add:

| Key | Value | Required | Description |
|-----|-------|----------|-------------|
| `PYTHONUNBUFFERED` | `1` | Optional | Ensures logs appear immediately |
| `FLASK_ENV` | `production` | Optional | Sets Flask to production mode |
| `PORT` | (Auto-set) | No | Render automatically sets this, don't override |

**Note**: Render automatically sets the `PORT` environment variable. Your Flask app should read it using:
```python
port = int(os.environ.get('PORT', 5000))
```
✅ Your `backend_server_example.py` already does this!

### Step 6: Create and Deploy

1. Review all settings
2. Click **"Create Web Service"**
3. Wait for the build process to complete (5-10 minutes first time)

---

## 📊 Deployment Process

### What Happens During Deployment

1. **Build Phase** (3-5 minutes):
   - Render clones your repository
   - Builds the Docker image from your Dockerfile
   - Installs system dependencies
   - Installs Python packages from `requirements.txt`
   - Copies your model and application files

2. **Deploy Phase** (1-2 minutes):
   - Starts the Flask server
   - Runs health checks
   - Makes the service accessible via HTTPS

### Monitoring Deployment

You can watch the deployment logs in real-time:

1. Click on your service name in the Render dashboard
2. Go to **"Logs"** tab
3. Watch for these key messages:
   - ✅ `Running in Docker environment`
   - ✅ `Using model: /app/assets/model.tflite`
   - ✅ `Starting fruit detection server...`
   - ✅ `Server will run on http://0.0.0.0:5000`

### Common Build Issues

**Issue**: Build fails with "Model not found"
- **Solution**: Verify `assets/model.tflite` is committed to Git
- Check: `git ls-files assets/model.tflite`

**Issue**: Build fails with "labels.txt not found"
- **Solution**: Verify `assets/labels.txt` is committed to Git

**Issue**: Build times out
- **Solution**: Free tier has slower builds, wait longer or upgrade

---

## ✅ Post-Deployment Configuration

### Step 1: Get Your Service URL

Once deployment succeeds:

1. In the Render dashboard, find your service
2. Look for the **"URL"** section (usually at the top)
3. Copy the URL, e.g., `https://fruit-detection-api.onrender.com`

### Step 2: Test the Deployment

#### Test Health Endpoint

Open your browser or use curl:
```bash
curl https://fruit-detection-api.onrender.com/health
```

Expected response:
```json
{
  "status": "ok",
  "model": "loaded"
}
```

#### Test Live Detection Endpoint

```bash
# Test with a sample image
curl -X POST https://fruit-detection-api.onrender.com/detect_live \
  -F "image=@/path/to/test/image.jpg" \
  -H "Content-Type: multipart/form-data"

# Expected response:
# {
#   "detections": [...],
#   "total_count": 3,
#   "active_objects": 3,
#   "tracker_status": {...}
# }
```

### Step 3: Verify Endpoints

Your deployed server should have these endpoints:

| Endpoint | Method | Description | Test URL |
|----------|--------|-------------|----------|
| `/health` | GET | Health check | `https://your-app.onrender.com/health` |
| `/detect` | POST | Single image detection | `https://your-app.onrender.com/detect` |
| `/detect_live` | POST | Live detection with tracking | `https://your-app.onrender.com/detect_live` |
| `/reset_tracker` | POST | Reset fruit counter | `https://your-app.onrender.com/reset_tracker` |
| `/tracker_status` | GET | Get tracker status | `https://your-app.onrender.com/tracker_status` |

---

## 📱 Update Flutter App for Live Detection

Now that your server is deployed, update your Flutter app to use it.

### Step 1: Update Backend Service

Edit `lib/frontend/services/backend_service.dart`:

**Option A: Use Render URL Only (Recommended for Production)**

```dart
class BackendDetectionService {
  // Use your Render URL for all platforms
  static String get defaultServerUrl {
    return 'https://fruit-detection-api.onrender.com';
    // ⚠️ Replace 'fruit-detection-api' with your actual service name
  }
  
  // ... rest of your code stays the same
}
```

**Option B: Support Both Local and Render (For Development)**

If you want to easily switch between local development and Render:

```dart
class BackendDetectionService {
  // Toggle between local and Render server
  static const bool USE_RENDER = true; // Set to false for local development
  static const String RENDER_URL = 'https://fruit-detection-api.onrender.com';
  
  static String get defaultServerUrl {
    if (USE_RENDER) {
      return RENDER_URL;
    }
    
    // Local development settings
    if (kIsWeb) {
      return 'http://localhost:5000';
    } else if (Platform.isAndroid) {
      return 'http://172.20.10.3:5000'; // Your laptop IP
    } else if (Platform.isIOS) {
      return 'http://172.20.10.3:5000'; // Your laptop IP
    } else {
      return 'http://localhost:5000';
    }
  }
  
  // ... rest of your code stays the same
}
```

**Quick Toggle**: Change `USE_RENDER` to `true` for production or `false` for local testing.

### Step 2: Test Connection from Flutter App

1. Open your Flutter app
2. Go to **Live Detection** page
3. Check the **Server Info** button (should show your Render URL)
4. Verify connection status is **"Connected"**

### Step 3: Test Live Detection

1. Start the camera in Live Detection
2. Point at fruits
3. Verify detection and counting works
4. Check that bounding boxes appear with IDs
5. Verify fruit counts update correctly

---

## 🧪 Testing Live Detection

### Complete Test Checklist

#### Pre-Testing Setup

- [ ] Render service is deployed and healthy
- [ ] Flutter app is updated with Render URL
- [ ] Mobile device and laptop are on the same Wi-Fi (for local testing)
- [ ] OR: Mobile device has internet access (for Render testing)

#### Local Testing (Render URL from Local Network)

If you want to test Render deployment from your local network:

1. **Find your Render URL**: `https://fruit-detection-api.onrender.com`
2. **Update Flutter app**: Use the Render URL directly
3. **Test from mobile**: Should connect via HTTPS

**Note**: Render free tier sleeps after 15 minutes. First request may take 30-60 seconds.

#### Remote Testing (From Anywhere)

1. **Update Flutter app** with Render URL
2. **Ensure mobile device has internet**
3. **Test Live Detection** - should work from anywhere in the world!

### Expected Behavior

✅ **Working Correctly**:
- Camera preview displays
- Fruits detected with bounding boxes
- Each fruit has a unique ID
- Count increases as new fruits appear
- Count doesn't reset when same fruit moves
- Server info shows "Connected" status
- Fruit type breakdown displays correctly

❌ **Issues to Watch For**:
- Slow first response (30-60s): Service was sleeping, normal for free tier
- Timeout errors: Check Render logs, service may be down
- No detections: Verify model file is in Docker image
- Connection refused: Verify URL is correct

---

## 🔧 Troubleshooting

### Issue: Service Won't Start

**Symptoms**: Deployment fails, service status shows "Failed"

**Solutions**:
1. Check **Logs** tab in Render dashboard
2. Look for error messages:
   - `Model not found`: Add `model.tflite` to Git
   - `Port already in use`: Check Dockerfile CMD
   - `Import error`: Check `requirements.txt`

**Debug Steps**:
```bash
# Test Docker build locally
docker build -t test-build .
docker run test-build
```

### Issue: Health Check Fails

**Symptoms**: Service starts but shows "Unhealthy"

**Solutions**:
1. Verify `/health` endpoint works: `curl https://your-app.onrender.com/health`
2. Check health check timeout in Dockerfile (should be 60s start-period)
3. Increase timeout if model loading is slow

### Issue: Slow First Request (Free Tier)

**Symptoms**: First request takes 30-60 seconds, then subsequent requests are fast

**Cause**: Render free tier puts services to sleep after 15 minutes of inactivity

**Solutions**:
- **Acceptable**: Normal behavior for free tier
- **Upgrade**: Switch to Starter plan ($7/month) for always-on service
- **Workaround**: Use a ping service to keep it awake (not recommended, violates ToS)

### Issue: Live Detection Not Working from Mobile

**Symptoms**: App shows connection error, no detections

**Checklist**:
1. ✅ Verify Render URL is correct in `backend_service.dart`
2. ✅ Test URL in browser: `https://your-app.onrender.com/health`
3. ✅ Check mobile device has internet connection
4. ✅ Verify Render service is "Live" (not sleeping)
5. ✅ Check Render logs for errors
6. ✅ Test with curl from command line

**Debug Command**:
```bash
# Test from your computer
curl -X POST https://your-app.onrender.com/detect_live \
  -F "image=@test_image.jpg" \
  -v
```

### Issue: Model Not Loading

**Symptoms**: `/health` returns error, logs show "Model not found"

**Solutions**:
1. Verify `model.tflite` is in Git:
   ```bash
   git ls-files assets/model.tflite
   ```
2. Check file size (should be > 0):
   ```bash
   git ls-files -s assets/model.tflite
   ```
3. Ensure Dockerfile copies the file:
   ```dockerfile
   COPY assets/model.tflite ./assets/model.tflite
   ```

### Issue: CORS Errors

**Symptoms**: Browser console shows CORS errors

**Solution**: Your Flask app already has `CORS(app)` enabled. If issues persist:
1. Check Render logs for CORS-related errors
2. Verify `flask-cors` is in `requirements.txt`

### Issue: Out of Memory

**Symptoms**: Service crashes, logs show "Killed" or "Out of memory"

**Solutions**:
1. **Free tier has 512MB RAM**: Model may be too large
2. **Optimize model**: Use quantized/smaller model
3. **Upgrade**: Starter plan has 512MB, Pro has more
4. **Reduce workers**: If using Gunicorn, use 1 worker

---

## ⚙️ Advanced Configuration

### Using Custom Domain

1. In Render dashboard, go to your service
2. Click **"Settings"** → **"Custom Domains"**
3. Add your domain
4. Update DNS records as instructed
5. Update Flutter app with new domain

### Auto-Deploy from Specific Branch

1. In service settings, change **"Branch"** to your branch name
2. Enable **"Auto-Deploy"**
3. Every push to that branch triggers deployment

### Environment-Specific Configuration

Add environment variables for different environments:

| Variable | Development | Production |
|----------|-------------|------------|
| `FLASK_ENV` | `development` | `production` |
| `LOG_LEVEL` | `DEBUG` | `INFO` |
| `MAX_UPLOAD_SIZE` | `10485760` | `5242880` |

### Monitoring and Logs

**View Logs**:
1. Click on your service in Render dashboard
2. Go to **"Logs"** tab
3. View real-time logs

**Log Retention**: Free tier keeps logs for 7 days

### Scaling (Paid Plans)

If you upgrade to Starter ($7/month) or higher:

1. **Workers**: Increase Gunicorn workers in `Dockerfile.production`
2. **Always-On**: Service never sleeps
3. **More RAM**: Better for larger models
4. **Custom domains**: Add your own domain

---

## 📊 Performance Optimization

### For Free Tier

- ✅ Use standard `Dockerfile` (not production)
- ✅ Single worker is sufficient
- ✅ Accept that first request may be slow

### For Paid Plans

- ✅ Use `Dockerfile.production` with Gunicorn
- ✅ Increase workers: `--workers 4`
- ✅ Enable HTTP/2 in Render settings
- ✅ Use CDN for static assets (if any)

---

## 🔐 Security Considerations

### Current Setup

✅ **Already Secure**:
- HTTPS automatically enabled by Render
- CORS configured for your Flutter app
- Non-root user in Docker (if using updated Dockerfile)

### Additional Security (Optional)

1. **API Keys**: Add API key authentication for endpoints
2. **Rate Limiting**: Implement rate limiting for abuse prevention
3. **Input Validation**: Already done in Flask app
4. **Request Size Limits**: Limit image upload size

---

## 📈 Monitoring Your Service

### Render Dashboard Metrics

View in Render dashboard:
- **Request Count**: Number of requests
- **Response Time**: Average response time
- **Error Rate**: Percentage of failed requests
- **Uptime**: Service availability

### Health Check Monitoring

Render automatically checks `/health` endpoint:
- **Interval**: Every 30 seconds
- **Timeout**: 10 seconds
- **Failure Action**: Service marked as unhealthy

---

## 🎉 Success Checklist

Once deployed, verify:

- [ ] Service URL is accessible: `https://your-app.onrender.com/health`
- [ ] Health endpoint returns: `{"status": "ok", "model": "loaded"}`
- [ ] Flutter app updated with Render URL
- [ ] Live Detection connects successfully
- [ ] Fruits are detected and counted correctly
- [ ] Tracking works (unique IDs, no duplicate counts)
- [ ] Server logs show successful requests

---

## 🆘 Getting Help

### Render Support

- **Documentation**: [render.com/docs](https://render.com/docs)
- **Community**: [community.render.com](https://community.render.com)
- **Status Page**: [status.render.com](https://status.render.com)

### Your Project Logs

If you encounter issues, check:
1. **Render Dashboard** → **Logs** tab
2. **Flutter App** → **Server Info** button in Live Detection
3. **Network Tab** in browser DevTools (if testing from web)

---

## 📝 Summary

**Quick Deployment Steps**:

1. ✅ Push code to GitHub
2. ✅ Create Render account
3. ✅ Create Web Service → Connect GitHub repo
4. ✅ Set Environment: Docker
5. ✅ Deploy and wait 5-10 minutes
6. ✅ Copy service URL
7. ✅ Update Flutter app with URL
8. ✅ Test Live Detection

**Your Live Detection Server URL**: 
```
https://your-service-name.onrender.com
```

**Replace in Flutter App**: `lib/frontend/services/backend_service.dart`

---

**🚀 You're all set! Your live detection server is now running on Render!**

For questions or issues, check the troubleshooting section or Render's documentation.

