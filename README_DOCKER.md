# 🐳 Quick Docker Guide

## Quick Start

### 1. Test Locally

```bash
# Build the Docker image
docker build -t fruit-detection-server .

# Run the container
docker run -d -p 5000:5000 --name fruit-server fruit-detection-server

# Check logs
docker logs -f fruit-server

# Test the server
curl http://localhost:5000/health

# Stop and remove
docker stop fruit-server && docker rm fruit-server
```

### 2. Using Docker Compose (Easier)

```bash
# Start the server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the server
docker-compose down
```

### 3. Deploy to Cloud

See `DEPLOYMENT_GUIDE.md` for detailed instructions on deploying to:
- **Render** (Easiest, recommended)
- **Railway** (Always-on)
- **Fly.io** (Production-ready)
- **Google Cloud Run** (Scalable)

## What's Included

- ✅ `Dockerfile` - Main Docker configuration
- ✅ `Dockerfile.production` - Production version with Gunicorn
- ✅ `docker-compose.yml` - Easy local development
- ✅ `requirements.txt` - Python dependencies
- ✅ `.dockerignore` - Exclude unnecessary files

## Important Notes

1. **Model File**: Make sure `assets/model.tflite` exists before building
2. **Labels File**: Make sure `assets/labels.txt` exists
3. **Port**: Default is 5000, can be changed with `PORT` environment variable
4. **First Build**: May take 5-10 minutes (downloading dependencies)

## Common Issues

- **Model not found**: Ensure `assets/model.tflite` is in your project
- **Port conflict**: Change port mapping: `-p 8080:5000`
- **Build fails**: Check internet connection and Docker disk space

