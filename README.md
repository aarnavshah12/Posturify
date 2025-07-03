# 🖥️ Slouching Detector - Windows Edition

A real-time posture monitoring application specifically optimized for Windows that uses computer vision to detect slouching and automatically adjusts system settings to encourage good posture.

## 🌟 Features

- **Real-time posture detection** using your trained Roboflow model
- **Windows-optimized brightness control** with smooth fade effects
- **Spotify integration**: Plays music for good posture, pauses for slouching  
- **Smart Windows sleep mode**: Uses Windows API for proper system sleep
- **Enhanced GUI** with Windows styling and real-time status updates
- **Windows API integration** for better system control

## 🎯 How It Works

1. **✅ Good Posture**: Full screen brightness with fade effect + Spotify music plays + sleep prevention
2. **⚠️ Slouching Detected**: Screen brightness quickly dims to 20% + music pauses + allows system sleep
3. **👤 User Absent**: Gradual brightness fade + system goes to sleep after 30 seconds

## Windows-Specific Optimizations

- **Native Windows API calls** for brightness, sleep, and system control
- **Multiple monitor support** for multi-display setups
- **Smooth brightness transitions** with fade effects
- **Windows sleep prevention** when user is actively maintaining good posture
- **Enhanced error handling** with WMI fallback methods

## Quick Start (Windows)

### Option 1: Easy Start (Recommended)
1. **Double-click `quick_start.bat`** - This will automatically:
   - Set up the virtual environment
   - Install all dependencies
   - Run configuration if needed
   - Start the GUI application

### Option 2: Manual Setup
1. **Run setup**:
   ```cmd
   python setup.py
   ```

2. **Start the application**:
   ```cmd
   python gui_app.py
   ```

## ⚙️ Configuration Required

### 🔐 Environment Variables Setup
Your API keys and settings are stored securely in a `.env` file that is ignored by git.

1. **Run the setup script**:
   ```cmd
   python setup.py
   ```

2. **Or manually edit the `.env` file**:
   ```env
   # Roboflow Configuration
   ROBOFLOW_API_KEY=your_actual_api_key_here
   ROBOFLOW_PROJECT=your_project_name
   ROBOFLOW_VERSION=1
   
   # Spotify Configuration
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   ```

### 🤖 Roboflow Model Setup
Your Roboflow model should detect these classes:
- `good_posture` - User sitting with proper posture
- `slouching` - User slouching or poor posture  
- No detection - User absent from camera

Get your credentials from [Roboflow](https://roboflow.com/)

### 🎵 Spotify App Setup
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Note the **Client ID** and **Client Secret**
4. Add `http://localhost:8888/callback` as a **Redirect URI**

## 🎮 Using the Application

### GUI Controls
- **▶️ Start Monitoring** - Begin posture detection
- **⏹️ Stop Monitoring** - Stop detection and restore normal settings
- **🧪 Test Components** - Test camera, brightness, Spotify, and system controls
- **💡 Test Brightness** - Test Windows brightness control with fade effects
- **😴 Test Sleep** - Test Windows sleep functionality (5-second delay)

### Real-time Status
- **🟢 Good Posture** - System optimized for productivity
- **🟡 Slouching** - Screen dimmed to encourage better posture
- **🔴 User Absent** - Preparing for sleep mode

## 🔧 Windows-Specific Settings

Edit your `.env` file to customize:

```env
# Brightness levels (0-100)
NORMAL_BRIGHTNESS=100      # Full brightness for good posture
SLOUCHING_BRIGHTNESS=20    # Dim brightness for slouching

# Timing
DETECTION_INTERVAL=1.0     # Seconds between posture checks
USER_ABSENT_TIMEOUT=30     # Seconds before sleep when absent

# Detection sensitivity
CONFIDENCE_THRESHOLD=0.5   # Model confidence threshold (0.0-1.0)
```

## 🔒 Security Features

- **Environment Variables**: All API keys stored in `.env` file
- **Git Ignore**: `.env` file is automatically ignored by git
- **Local Processing**: Video processed locally on your machine
- **Secure Storage**: No sensitive data hardcoded in source files

## 🛠️ Troubleshooting (Windows)

### 💡 Brightness Issues
- **Admin Rights**: Some Windows systems require administrator privileges for brightness control
- **Multiple Monitors**: The app automatically detects all monitors
- **Fallback Method**: If standard control fails, WMI method is used automatically

### 📹 Camera Issues
- Ensure webcam is not in use by other applications
- Try different camera indices (0, 1, 2) if needed
- Check Windows Camera privacy settings

### 🎵 Spotify Issues
- Make sure Spotify desktop app is running and you're logged in
- Verify your Spotify app credentials are correct
- Check that redirect URI matches exactly: `http://localhost:8888/callback`

### 😴 Sleep Issues
- Some Windows systems may have sleep disabled in power settings
- Corporate/managed systems might have sleep restrictions
- The app uses Windows API calls for reliable sleep functionality

### 🤖 Roboflow Issues
- Verify internet connection for model inference
- Check API key and project details are correct
- Ensure model is published and accessible

## 📁 File Structure

```
slouching_detector/
├── 🖥️ start.bat                    # Windows startup script
├── 🎮 gui_app.py                   # Main GUI application
├── 🧠 slouching_detector.py        # Core detection logic  
├── 💡 brightness_controller.py     # Windows brightness control
├── 🎵 spotify_controller.py        # Spotify integration
├── 😴 system_controller.py         # Windows system control
├── ⚙️ config.py                    # Configuration loader (reads .env)
├── 🔧 setup.py                     # Interactive setup wizard
├── 🧪 test_components.py           # Component testing
├── 📦 requirements.txt             # Python dependencies
├── 🔒 .env                         # Environment variables (git ignored)
├── 📝 .env.example                 # Environment template
├── 🚫 .gitignore                   # Git ignore rules
└── 📖 README.md                    # This documentation
```

## 🔒 Privacy & Security

- **Local Processing**: Video is processed locally on your Windows machine
- **No Video Storage**: No video data is stored or sent anywhere except Roboflow inference
- **API Usage**: Only Roboflow model inference and Spotify control require internet
- **Windows Integration**: Uses standard Windows APIs for system control

## 🎯 Windows Performance Tips

1. **Close unnecessary applications** to free up camera and system resources
2. **Ensure good lighting** for better posture detection accuracy  
3. **Position camera at eye level** for optimal posture monitoring
4. **Keep Spotify running** in the background for music features
5. **Run as administrator** if experiencing brightness control issues

## 🆘 Getting Help

1. **Check the Activity Log** in the GUI for detailed error messages
2. **Run component tests** to identify which features are working
3. **Review Windows Event Viewer** for system-level issues
4. **Ensure all dependencies** are properly installed

## 🔄 Updates & Maintenance

- Keep your Roboflow model updated for better accuracy
- Update Python packages regularly: `pip install -r requirements.txt --upgrade`
- Check Windows Updates for latest camera and display drivers
