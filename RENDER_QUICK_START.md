# 🚀 Render Quick Start Guide

**Fast deployment checklist for your Fruit Detection server on Render.**

## ⚡ Quick Steps

### 1. Prepare Repository
```bash
# Verify files are in Git
git ls-files assets/model.tflite
git ls-files assets/labels.txt
git ls-files Dockerfile

# Commit and push everything
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Deploy on Render

1. Go to [render.com](https://render.com) → Sign up/Sign in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `fruit-detection-api`
   - **Environment**: `Docker`
   - **Region**: Choose closest to you
   - **Plan**: `Free`
5. Click **"Create Web Service"**
6. Wait 5-10 minutes for deployment

### 3. Get Your URL

After deployment:
- Copy your service URL: `https://fruit-detection-api.onrender.com`
- Test: `curl https://fruit-detection-api.onrender.com/health`

### 4. Update Flutter App

Edit `lib/frontend/services/backend_service.dart`:
```dart
static String get defaultServerUrl {
  return 'https://fruit-detection-api.onrender.com'; // Your Render URL
}
```

### 5. Test Live Detection

1. Open Flutter app
2. Go to Live Detection page
3. Start camera
4. Verify detections work

## ✅ Checklist

- [ ] Code pushed to GitHub
- [ ] Model files committed to Git
- [ ] Render service deployed
- [ ] Health endpoint works
- [ ] Flutter app updated with URL
- [ ] Live Detection tested

## 🔗 Important URLs

- **Render Dashboard**: [dashboard.render.com](https://dashboard.render.com)
- **Full Guide**: See `RENDER_DEPLOYMENT_GUIDE.md`
- **Troubleshooting**: Check Render logs in dashboard

## ⚠️ Notes

- Free tier sleeps after 15 min inactivity (30-60s wake time)
- First deployment takes 5-10 minutes
- Service URL format: `https://your-service-name.onrender.com`

---

**Need help?** See the detailed guide: `RENDER_DEPLOYMENT_GUIDE.md`

