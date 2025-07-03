# Slouching Detector Configuration
# This file loads configuration from environment variables (.env file)

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Roboflow Configuration
ROBOFLOW_API_KEY = os.getenv('ROBOFLOW_API_KEY', 'your_roboflow_api_key_here')
ROBOFLOW_PROJECT = os.getenv('ROBOFLOW_PROJECT', 'your_project_name')
ROBOFLOW_VERSION = int(os.getenv('ROBOFLOW_VERSION', '1'))

# Spotify Configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', 'your_spotify_client_id')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', 'your_spotify_client_secret')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')

# Detection Settings
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.5'))
DETECTION_INTERVAL = float(os.getenv('DETECTION_INTERVAL', '0.2'))  # Even faster - 5 times per second
DISPLAY_INTERVAL = float(os.getenv('DISPLAY_INTERVAL', '0.03'))  # Display updates ~33 FPS

# Brightness Settings
NORMAL_BRIGHTNESS = int(os.getenv('NORMAL_BRIGHTNESS', '100'))
SLOUCHING_BRIGHTNESS = int(os.getenv('SLOUCHING_BRIGHTNESS', '20'))

# Sleep Mode Settings
USER_ABSENT_TIMEOUT = 3  # Timeout in seconds for user absence before system sleeps

def validate_config():
    """Validate that all required configuration is present"""
    missing_vars = []
    
    if ROBOFLOW_API_KEY == 'your_roboflow_api_key_here':
        missing_vars.append('ROBOFLOW_API_KEY')
    
    if ROBOFLOW_PROJECT == 'your_project_name':
        missing_vars.append('ROBOFLOW_PROJECT')
        
    if SPOTIFY_CLIENT_ID == 'your_spotify_client_id':
        missing_vars.append('SPOTIFY_CLIENT_ID')
        
    if SPOTIFY_CLIENT_SECRET == 'your_spotify_client_secret':
        missing_vars.append('SPOTIFY_CLIENT_SECRET')
    
    return missing_vars

def print_config_status():
    """Print current configuration status"""
    print("Configuration Status:")
    print(f"   Roboflow API Key: {'Set' if ROBOFLOW_API_KEY != 'your_roboflow_api_key_here' else 'Not set'}")
    print(f"   Roboflow Project: {ROBOFLOW_PROJECT}")
    print(f"   Spotify Client ID: {'Set' if SPOTIFY_CLIENT_ID != 'your_spotify_client_id' else 'Not set'}")
    print(f"   Confidence Threshold: {CONFIDENCE_THRESHOLD}")
    print(f"   Detection Interval: {DETECTION_INTERVAL}s")
    print(f"   Normal Brightness: {NORMAL_BRIGHTNESS}%")
    print(f"   Slouching Brightness: {SLOUCHING_BRIGHTNESS}%")
    print(f"   User Absent Timeout: {USER_ABSENT_TIMEOUT}s")
