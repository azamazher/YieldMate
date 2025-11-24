# Git Repository Setup Instructions

## Current Status
- Git repository initialized
- Initial commit created with all project files
- .gitignore updated to exclude model files and build artifacts

## Files Excluded from Git
The following files/folders are NOT committed (as per .gitignore):
- `assets/model.tflite` - Model file (too large for git)
- `build/` - Flutter build artifacts
- `.dart_tool/` - Dart tooling cache
- `android/.gradle/` - Gradle cache
- `ios/Pods/` - CocoaPods dependencies (will be regenerated)
- `*.iml` - IntelliJ module files
- `__pycache__/` - Python cache

## Next Steps: Create Remote Repository

### Option 1: GitHub

1. **Create a new repository on GitHub:**
   - Go to https://github.com/new
   - Repository name: `Fruit-Detection` (or your preferred name)
   - Description: "YieldMate - Smart Fruit Detection app using AI and YOLOv8 model"
   - Choose Public or Private
   - DO NOT initialize with README, .gitignore, or license (we already have these)
   - Click "Create repository"

2. **Connect your local repository to GitHub:**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

### Option 2: GitLab

1. **Create a new project on GitLab:**
   - Go to https://gitlab.com/projects/new
   - Project name: `Fruit-Detection`
   - Visibility: Public or Private
   - DO NOT initialize with README
   - Click "Create project"

2. **Connect your local repository to GitLab:**
   ```bash
   git remote add origin https://gitlab.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

### Option 3: Bitbucket

1. **Create a new repository on Bitbucket:**
   - Go to https://bitbucket.org/repo/create
   - Repository name: `Fruit-Detection`
   - Access level: Private or Public
   - DO NOT initialize with README
   - Click "Create repository"

2. **Connect your local repository to Bitbucket:**
   ```bash
   git remote add origin https://bitbucket.org/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

## Important Notes

### Model File
The `assets/model.tflite` file is NOT included in the repository because:
- It's too large for git (typically 10-50MB+)
- Git repositories work better without large binary files

**To share the model:**
- Use Git LFS (Large File Storage) if you need version control
- Upload to cloud storage (Google Drive, Dropbox, etc.) and share the link
- Include download instructions in README.md

### Dependencies
When someone clones the repository, they need to:
1. Run `flutter pub get` to install Flutter dependencies
2. Run `cd ios && pod install` for iOS dependencies
3. Download the model file separately (if needed)

## Verify Your Setup

After pushing, verify everything is uploaded:
```bash
git log --oneline
git remote -v
git status
```

## Future Commits

For future changes:
```bash
git add .
git commit -m "Your commit message"
git push
```

