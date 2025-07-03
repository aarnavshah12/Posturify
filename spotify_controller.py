import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging
import config

logger = logging.getLogger(__name__)

class SpotifyController:
    def __init__(self):
        self.sp = None
        self.is_initialized = False
        self.current_playback = None
    
    def initialize(self):
        """Initialize Spotify client with detailed logging"""
        if self.is_initialized:
            return True
            
        logger.info("Attempting to initialize Spotify...")
        try:
            scope = "user-read-playback-state,user-modify-playback-state,user-read-currently-playing,user-read-recently-played,user-top-read,user-library-read,playlist-read-private"
            
            # Set a higher timeout for the auth manager
            auth_manager = SpotifyOAuth(
                client_id=config.SPOTIFY_CLIENT_ID,
                client_secret=config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=config.SPOTIFY_REDIRECT_URI,
                scope=scope,
                open_browser=True, # Explicitly open browser
                cache_path="./.spotify_cache" # Ensure cache is local
            )
            
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Test connection by fetching user info
            user = self.sp.current_user()
            if user and 'display_name' in user:
                logger.info(f"Spotify successfully initialized for user: {user['display_name']}")
                
                # Check Premium status
                premium_status = self.check_premium_status()
                if premium_status is True:
                    logger.info("Spotify Premium detected - Music control enabled")
                elif premium_status is False:
                    logger.warning("Spotify Free detected - Music control may be limited")
                else:
                    logger.info("Spotify Premium status unknown - Assuming Premium for music control")
                
                self.is_initialized = True
                return True
            else:
                logger.error("Spotify authentication failed: Could not retrieve user information.")
                self.is_initialized = False
                return False
                
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Spotify API Error during initialization: {e}")
            logger.info("Please check your Spotify API credentials in .env and ensure you have an internet connection.")
            self.is_initialized = False
            return False
        except Exception as e:
            import traceback
            logger.error(f"An unexpected error occurred during Spotify initialization: {e}")
            logger.error(traceback.format_exc())
            logger.info("Music control will be disabled.")
            self.is_initialized = False
            return False
    
    def get_current_playback(self):
        """Get current playback status"""
        if not self.is_initialized:
            return None
        
        try:
            self.current_playback = self.sp.current_playback()
            return self.current_playback
        except Exception as e:
            logger.error(f"Failed to get current playback: {e}")
            return None
    
    def play_music(self):
        """Start/resume music playback with enhanced device handling"""
        if not self.is_initialized:
            logger.warning("Spotify not initialized - cannot play music")
            return False
        
        try:
            logger.info("Attempting to play music...")
            current = self.get_current_playback()
            
            if current is None:
                logger.info("No active playback found. Checking available devices...")
                # No active device or no music in queue
                # Try to start playback on available device
                devices = self.sp.devices()
                logger.info(f"Available devices: {[d['name'] + ' (' + d['type'] + ')' for d in devices['devices']] if devices and devices['devices'] else 'None'}")
                
                if devices and len(devices['devices']) > 0:
                    # Find an active device or use the first available one
                    active_device = None
                    for device in devices['devices']:
                        if device['is_active']:
                            active_device = device
                            break
                    
                    if not active_device:
                        active_device = devices['devices'][0]
                    
                    device_id = active_device['id']
                    device_name = active_device['name']
                    logger.info(f"Using device: {device_name}")
                    
                    # Try to get user's saved tracks or recently played to start something
                    try:
                        # Simplified approach - just try to start playback
                        logger.info("Attempting to start/resume playback...")
                        self.sp.start_playback(device_id=device_id)
                        logger.info("Started playback successfully")
                    except Exception as e:
                        if "No active device found" in str(e):
                            logger.error("No active Spotify device found")
                            logger.info("Tip: Open Spotify app and start playing any song first")
                            return False
                        elif "Premium required" in str(e) or "PREMIUM_REQUIRED" in str(e):
                            logger.error("Spotify Premium required for playback control")
                            logger.info("Please ensure your Spotify Premium subscription is active")
                            return False
                        else:
                            logger.warning(f"Could not start playback: {e}")
                            logger.info("Tip: Open Spotify app and start playing any song first, then try again")
                            return False
                    
                    logger.info("Started music playback successfully")
                else:
                    logger.warning("No Spotify devices available")
                    logger.info("Tip: Open Spotify on your computer or phone first")
                    return False
            elif not current['is_playing']:
                # Resume playback
                logger.info("Resuming paused music...")
                self.sp.start_playback()
                logger.info("Resumed music playback")
            else:
                logger.info("Music is already playing")
            
            return True
            
        except spotipy.exceptions.SpotifyException as e:
            if "Premium required" in str(e) or "PREMIUM_REQUIRED" in str(e):
                logger.error("Spotify Premium subscription required for playback control")
                logger.info("Spotify Free users cannot control playback via API - consider upgrading to Premium")
                logger.info("Alternative: Music control will be disabled, but posture detection will continue")
                return False
            else:
                logger.error(f"Spotify API Error: {e}")
                logger.info("Tip: Make sure Spotify is open and you have an active internet connection")
                return False
        except Exception as e:
            logger.error(f"Failed to play music: {e}")
            logger.info("Tip: Make sure Spotify is open and you have an active internet connection")
            return False
    
    def pause_music(self):
        """Pause music playback"""
        if not self.is_initialized:
            logger.warning("Spotify not initialized - cannot pause music")
            return False
        
        try:
            current = self.get_current_playback()
            
            if current and current['is_playing']:
                self.sp.pause_playback()
                logger.info("Paused music playback")
                return True
            else:
                logger.info("Music is not currently playing")
                return False
                
        except Exception as e:
            logger.error(f"Failed to pause music: {e}")
            return False
    
    def set_volume(self, volume_percent):
        """Set playback volume (0-100)"""
        if not self.is_initialized:
            return False
        
        try:
            if volume_percent < 0:
                volume_percent = 0
            elif volume_percent > 100:
                volume_percent = 100
            
            self.sp.volume(volume_percent)
            logger.info(f"Set Spotify volume to {volume_percent}%")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False
    
    def check_premium_status(self):
        """Check if user has Spotify Premium with enhanced detection"""
        if not self.is_initialized:
            return None
        
        try:
            user = self.sp.current_user()
            if user:
                logger.debug(f"User info keys: {list(user.keys())}")  # Debug: show available keys
                
                if 'product' in user:
                    product = user['product'].lower()
                    logger.info(f"Spotify account product: '{product}'")
                    
                    # Check for various Premium indicators
                    is_premium = product in ['premium', 'premium_student', 'premium_family', 'premium_duo']
                    
                    if is_premium:
                        logger.info(f"Premium account detected: {product}")
                        return True
                    else:
                        logger.warning(f"Free account detected: {product}")
                        return False
                else:
                    logger.info("No 'product' field in user info - checking playback capabilities...")
                    
                    # Test 1: Try to get available devices (Premium feature for remote control)
                    try:
                        devices = self.sp.devices()
                        if devices and 'devices' in devices:
                            logger.info(f"Found {len(devices['devices'])} available device(s)")
                            if len(devices['devices']) > 0:
                                logger.info("Device control available - likely Premium account")
                                return True
                    except Exception as device_error:
                        logger.debug(f"Device check failed: {device_error}")
                    
                    # Test 2: Try to get current playback state
                    try:
                        current = self.sp.current_playback()
                        if current:
                            logger.info("Playback state accessible - likely Premium account")
                            return True
                        else:
                            logger.info("No active playback found")
                    except Exception as playback_error:
                        logger.debug(f"Playback check failed: {playback_error}")
                    
                    # Test 3: Since you said you have Premium and can hear music, assume Premium
                    logger.info("Cannot determine status from API - Assuming Premium (music control works)")
                    return None  # Unknown status, but assume Premium
            else:
                logger.warning("Could not retrieve user information")
                return None
        except Exception as e:
            logger.error(f"Failed to check Premium status: {e}")
            return None
