# Render Deployment Instructions

## Prerequisites
- Docker is installed locally (for testing)
- Git repository is set up
- Render account created

## Deployment Steps

### 1. Connect Repository to Render
- Go to https://render.com/
- Click "New +" → "Web Service"
- Connect your GitHub repository
- Select the `quiz-platform` repository

### 2. Configure Service Settings
After connecting the repository, configure:

**Settings Required:**
- **Name**: `quiz-platform`
- **Runtime**: `Docker` (NOT Python!)
- **Build Command**: (Leave empty - Docker will use Dockerfile)
- **Start Command**: (Leave empty - Docker will use CMD from Dockerfile)

**Environment Variables** (add these in Render Dashboard):
```
DEBUG=false
SECRET_KEY=your-production-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
PORT=8000
```

### 3. Deploy
- Click "Create Web Service"
- Render will automatically:
  - Detect the Dockerfile
  - Build the Docker image
  - Install Java, Python, GCC, and all dependencies
  - Run migrations
  - Collect static files
  - Deploy the service

### 4. Verify Deployment
Once deployed:
- Check logs for Java installation success
- Visit: `https://your-service.onrender.com/health/` → should show `{"status": "healthy"}`
- Test Java code execution in the quiz platform

## Troubleshooting

### If you still get "javac: No such file" error:

1. **Check Render Build Logs:**
   - Go to your service on Render Dashboard
   - Click "Logs"
   - Look for Java installation output
   - If you see errors, try "Manual Deploy" again

2. **Force rebuild:**
   - Push a new commit: `git commit --allow-empty -m "Trigger rebuild"`
   - `git push origin main`

3. **Check Docker is being used:**
   - In Render Dashboard → Service Settings
   - Verify "Runtime" is set to "Docker" (not "Python")

4. **Verify build log shows:**
   ```
   Java version:
   openjdk version "11..."
   Javac version:
   javac 11...
   ```

## Key Files

- **Dockerfile** - Installs Python, Java, GCC, Django dependencies
- **.dockerignore** - Optimizes Docker build size
- **requirements.txt** - Python dependencies
- **core/urls.py** - Health check endpoint for Render

## Port Configuration

- Service runs on port 8000 (configured in Dockerfile)
- Render exposes via public HTTPS URL automatically
