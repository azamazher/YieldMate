# 🚀 Deployment Guide: Fruit Detection Flask Server

This guide will help you deploy your Flask server to a free cloud hosting platform using Docker.

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Docker Testing](#local-docker-testing)
3. [Free Server Options](#free-server-options)
4. [Deployment Steps](#deployment-steps)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)

---

## 📦 Prerequisites

Before deploying, ensure you have:
- ✅ Docker installed on your local machine ([Download Docker](https://www.docker.com/products/docker-desktop))
- ✅ Git installed
- ✅ A GitHub account (for most free hosting platforms)
- ✅ Your `model.tflite` and `labels.txt` files in the `assets/` folder

---

## 🐳 Local Docker Testing

### Step 1: Build the Docker Image

```bash
# Navigate to your project directory
cd /path/to/Fruit-Detection

# Build the Docker image
docker build -t fruit-detection-server .

# Or using docker-compose
docker-compose build
```

### Step 2: Run the Container

```bash
# Run with Docker
docker run -d -p 5000:5000 --name fruit-server fruit-detection-server

# Or using docker-compose (recommended)
docker-compose up -d
```

### Step 3: Test the Server

```bash
# Check if server is running
curl http://localhost:5000/health

# Expected response:
# {"status": "ok", "model": "loaded"}
```

### Step 4: Stop the Container

```bash
# Stop and remove
docker stop fruit-server
docker rm fruit-server

# Or with docker-compose
docker-compose down
```

---

## 🌐 Free Server Options

### 1. **Render** (⭐ Recommended - Easiest)
- **Free Tier**: 750 hours/month, sleeps after 15 min inactivity
- **Pros**: Very easy setup, auto-deploy from GitHub, free SSL
- **Cons**: Spins down when idle (first request takes ~30s to wake)
- **Best For**: Testing, small projects, development
- **Website**: [render.com](https://render.com)

### 2. **Railway**
- **Free Tier**: $5 credit/month, very generous
- **Pros**: Always-on, fast, easy GitHub integration
- **Cons**: Limited free credit (may need to upgrade)
- **Best For**: Production apps, always-on services
- **Website**: [railway.app](https://railway.app)

### 3. **Fly.io**
- **Free Tier**: 3 shared-cpu VMs, 3GB persistent storage
- **Pros**: Great for Docker, global regions, always-on
- **Cons**: Slightly more complex setup
- **Best For**: Production apps, global deployment
- **Website**: [fly.io](https://fly.io)

### 4. **Render Alternative: PythonAnywhere** (No Docker needed)
- **Free Tier**: 1 web app, limited CPU
- **Pros**: Simple Python hosting, no Docker needed
- **Cons**: Can't run Docker, limited resources
- **Best For**: Simple Flask apps without Docker

### 5. **Google Cloud Run** (Free Tier)
- **Free Tier**: 2 million requests/month, 360,000 GB-seconds
- **Pros**: Pay-per-use, scales to zero, auto-scaling
- **Cons**: More complex setup, requires Google Cloud account
- **Best For**: Production apps, high traffic
- **Website**: [cloud.google.com/run](https://cloud.google.com/run)

---

## 🚀 Deployment Steps

### Option A: Deploy to Render (Recommended for Beginners)

#### Step 1: Prepare Your Repository
```bash
# Make sure your code is on GitHub
git add .
git commit -m "Add Docker configuration"
git push origin main
```

#### Step 2: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New +" → "Web Service"

#### Step 3: Connect Repository
1. Connect your GitHub account
2. Select your `Fruit-Detection` repository
3. Choose the branch (usually `main`)

#### Step 4: Configure Service
- **Name**: `fruit-detection-api` (or any name)
- **Environment**: `Docker`
- **Region**: Choose closest to you
- **Branch**: `main`
- **Root Directory**: Leave empty (or `./` if needed)
- **Dockerfile Path**: `Dockerfile` (auto-detected)
- **Docker Context**: `.` (root)
- **Plan**: `Free`

#### Step 5: Environment Variables
Add these if needed (usually not required):
```
FLASK_ENV=production
PYTHONUNBUFFERED=1
```

#### Step 6: Deploy
1. Click "Create Web Service"
2. Wait for build (5-10 minutes first time)
3. Copy your service URL (e.g., `https://fruit-detection-api.onrender.com`)

#### Step 7: Update Flutter App
Update `lib/frontend/services/backend_service.dart`:
```dart
static String get defaultServerUrl {
  return 'https://your-app-name.onrender.com'; // Replace with your Render URL
}
```

---

### Option B: Deploy to Railway

#### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub

#### Step 2: Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your repository

#### Step 3: Configure
- Railway auto-detects Docker
- Add port: `5000`
- Add start command (optional): `python app.py`

#### Step 4: Deploy
- Railway automatically builds and deploys
- Get your URL from the project dashboard

---

### Option C: Deploy to Fly.io

#### Step 1: Install Fly CLI
```bash
# macOS
brew install flyctl

# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex

# Linux
curl -L https://fly.io/install.sh | sh
```

#### Step 2: Login
```bash
fly auth login
```

#### Step 3: Create Fly App
```bash
cd /path/to/Fruit-Detection
fly launch
```

Follow the prompts:
- App name: `fruit-detection-api` (or auto-generated)
- Region: Choose closest
- Postgres/Redis: No (for now)

#### Step 4: Deploy
```bash
fly deploy
```

#### Step 5: Get URL
```bash
fly info
# Shows your app URL
```

---

## ⚙️ Configuration

### Update Flask Server for Production

Edit `lib/backend/backend_server_example.py` for production:

```python
if __name__ == '__main__':
    # Production: Use environment variable for port
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False for production
```

Or use Gunicorn (included in requirements.txt):

```dockerfile
# In Dockerfile, change CMD to:
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
```

### Environment Variables

Common environment variables you might need:
```env
PORT=5000
FLASK_ENV=production
PYTHONUNBUFFERED=1
```

---

## 🔧 Troubleshooting

### Issue: "Model not found" error
**Solution**: Ensure `assets/model.tflite` and `assets/labels.txt` are in your repository and copied to Docker image.

### Issue: Container exits immediately
**Solution**: Check logs:
```bash
docker logs fruit-server
# Or
docker-compose logs
```

### Issue: Port already in use
**Solution**: Change port mapping:
```yaml
# In docker-compose.yml
ports:
  - "8080:5000"  # Use 8080 on host instead
```

### Issue: Slow first request (Render)
**Solution**: This is normal for Render free tier. The service "sleeps" after 15 minutes. First request wakes it up (~30s delay).

### Issue: Out of memory
**Solution**: 
- Use a smaller model if possible
- Upgrade to paid tier for more resources
- Use model quantization

---

## 📱 Update Flutter App

After deployment, update your Flutter app to use the server URL:

```dart
// lib/frontend/services/backend_service.dart
class BackendDetectionService {
  static String get defaultServerUrl {
    // Replace with your actual server URL
    return 'https://your-app-name.onrender.com';
    // Or for Railway: 'https://your-app.railway.app'
    // Or for Fly.io: 'https://your-app.fly.dev'
  }
}
```

---

## ✅ Quick Commands Reference

```bash
# Build image
docker build -t fruit-detection-server .

# Run container
docker run -d -p 5000:5000 --name fruit-server fruit-detection-server

# View logs
docker logs -f fruit-server

# Stop container
docker stop fruit-server

# Remove container
docker rm fruit-server

# Using docker-compose
docker-compose up -d          # Start
docker-compose down           # Stop
docker-compose logs -f        # View logs
docker-compose restart        # Restart
```

---

## 🎉 Next Steps

1. ✅ Test locally with Docker
2. ✅ Choose a hosting platform
3. ✅ Deploy using the steps above
4. ✅ Update Flutter app with server URL
5. ✅ Test detection from your mobile app

Good luck with your deployment! 🚀

