import cv2
import numpy as np
from inference_sdk import InferenceHTTPClient
import time
import threading
import logging
from datetime import datetime, timedelta
from enum import Enum
import config
from brightness_controller import BrightnessController
from spotify_controller import SpotifyController
from system_controller import SystemController

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostureState(Enum):
    GOOD_POSTURE = "good_posture"
    SLOUCHING = "slouching"
    USER_ABSENT = "user_absent"

class SlouchingDetector:
    def __init__(self, shutdown_callback=None):
        self.client = None
        self.model_id = None
        self.current_state = PostureState.USER_ABSENT
        self.last_detection_time = datetime.now()
        self.user_absent_start = None
        self.monitoring_start_time = None  # Track when monitoring actually started
        self.running = False
        self.shutdown_callback = shutdown_callback
        self.state_lock = threading.Lock()
        
        # State change debouncing
        self.last_state_change_time = datetime.now()
        self.state_change_debounce_duration = 0.5  # Reduce to 0.5 seconds for more responsive behavior
        
        # Initialize controllers
        self.brightness_controller = BrightnessController()
        self.spotify_controller = SpotifyController()
        self.system_controller = SystemController()
        
        # Initialize camera
        self.cap = None
        
    def initialize_roboflow(self):
        """Initialize Roboflow model using inference-sdk"""
        try:
            # Create inference client
            self.client = InferenceHTTPClient(
                api_url="https://detect.roboflow.com",
                api_key=config.ROBOFLOW_API_KEY
            )
            
            # Build the correct model ID format: project_id/model_version_id
            if '/' in config.ROBOFLOW_PROJECT:
                _, project_name = config.ROBOFLOW_PROJECT.split('/', 1)
                self.model_id = f"{project_name}/{config.ROBOFLOW_VERSION}"
            else:
                self.model_id = f"{config.ROBOFLOW_PROJECT}/{config.ROBOFLOW_VERSION}"
            
            logger.info(f"Roboflow model initialized successfully for {self.model_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Roboflow: {e}")
            return False
    
    def initialize_camera(self):
        """Initialize camera with multiple fallback options"""
        try:
            # Try different camera backends and indices
            camera_options = [
                (0, cv2.CAP_DSHOW),  # DirectShow (Windows default)
                (0, cv2.CAP_MSMF),   # Microsoft Media Foundation
                (0, cv2.CAP_ANY),    # Auto-select backend
                (1, cv2.CAP_DSHOW),  # Second camera with DirectShow
                (1, cv2.CAP_ANY),    # Second camera with auto-select
            ]
            
            for camera_index, backend in camera_options:
                try:
                    logger.info(f"Trying camera {camera_index} with backend {backend}")
                    self.cap = cv2.VideoCapture(camera_index, backend)
                    
                    if self.cap.isOpened():
                        # Test if we can actually read a frame
                        ret, test_frame = self.cap.read()
                        if ret and test_frame is not None:
                            logger.info(f"Camera {camera_index} initialized successfully with backend {backend}")
                            # Set camera properties for better performance and speed
                            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            self.cap.set(cv2.CAP_PROP_FPS, 30)  # Higher frame rate
                            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for lower latency
                            # Disable auto-exposure and auto-focus for consistent performance
                            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual exposure
                            return True
                        else:
                            self.cap.release()
                            
                except Exception as e:
                    logger.warning(f"Camera {camera_index} with backend {backend} failed: {e}")
                    if hasattr(self, 'cap') and self.cap:
                        self.cap.release()
                    continue
            
            raise Exception("No working camera found")
            
        except Exception as e:
            logger.error(f"Failed to initialize any camera: {e}")
            return False
    
    def detect_posture(self, frame):
        """Detect posture from frame using Roboflow inference SDK"""
        try:
            logger.debug("🔍 Starting posture detection...")
            # Save frame temporarily for inference
            temp_path = "temp_frame.jpg"
            cv2.imwrite(temp_path, frame)
            logger.debug(f"📸 Frame saved to {temp_path}")
            
            # Get prediction using inference SDK
            logger.debug("🤖 Calling Roboflow inference...")
            result = self.client.infer(temp_path, model_id=self.model_id)
            logger.debug(f"📊 Inference result: {result}")
            
            if 'predictions' in result and len(result['predictions']) > 0:
                # Get the prediction with highest confidence
                best_prediction = max(result['predictions'], key=lambda x: x.get('confidence', 0))
                detected_class = best_prediction.get('class', 'unknown')
                confidence = best_prediction.get('confidence', 0)
                
                logger.info(f"Detected: {detected_class} with confidence: {confidence:.2f}")
                
                # Only accept predictions with reasonable confidence
                if confidence < 0.5:
                    logger.info("Low confidence detection, treating as user absent")
                    return PostureState.USER_ABSENT
                
                # Map detected classes to posture states
                # Update these mappings based on your actual model's output classes
                if detected_class in ['proper', 'good_posture', 'sitting']:
                    return PostureState.GOOD_POSTURE
                elif detected_class in ['slouching', 'bad_posture']:
                    return PostureState.SLOUCHING
                elif detected_class in ['leave', 'standing', 'absent', 'no_person']:
                    return PostureState.USER_ABSENT
                else:
                    # Unknown class - log it and default to user absent
                    logger.warning(f"Unknown class detected: {detected_class}")
                    return PostureState.USER_ABSENT
            else:
                # No predictions found - user is absent
                logger.info("No predictions found - user absent")
                return PostureState.USER_ABSENT
                
        except Exception as e:
            logger.error(f"Error in posture detection: {e}")
            logger.debug(f"Exception details: {traceback.format_exc()}")
            return PostureState.USER_ABSENT
    
    def handle_state_change(self, new_state):
        """Handle state transitions and trigger appropriate actions"""
        # Convert string to enum if needed
        if isinstance(new_state, str):
            try:
                new_state = PostureState(new_state)
            except ValueError:
                logger.warning(f"Unknown state string: {new_state}, defaulting to USER_ABSENT")
                new_state = PostureState.USER_ABSENT
        
        # Add debouncing to prevent rapid state changes
        current_time = datetime.now()
        time_since_last_change = (current_time - self.last_state_change_time).total_seconds()
        
        # Log every state detection for debugging (after ensuring new_state is an enum)
        logger.debug(f"State detection: {new_state.value} (current: {self.current_state.value})")
        
        # If state changes, log it and perform initial actions.
        if new_state != self.current_state:
            # Only allow state changes if enough time has passed (debouncing)
            if time_since_last_change >= self.state_change_debounce_duration:
                logger.info(f"State change: {self.current_state} -> {new_state}")
                self.current_state = new_state
                self.last_state_change_time = current_time
                
                if new_state == PostureState.GOOD_POSTURE:
                    self.handle_good_posture()
                elif new_state == PostureState.SLOUCHING:
                    self.handle_slouching()
                elif new_state == PostureState.USER_ABSENT:
                    # This is the first time we detect the user is absent
                    self.handle_user_absent()
            else:
                logger.debug(f"State change ignored due to debouncing: {self.current_state} -> {new_state} (time since last change: {time_since_last_change:.1f}s)")
        
        # IMPORTANT: Always check user absent state, even if no state change
        # This ensures the sleep timer continues to run
        elif new_state == PostureState.USER_ABSENT:
            self.handle_user_absent()
    
    def handle_good_posture(self):
        """Handle good posture state - Windows optimized"""
        logger.info("Good posture detected - Setting full brightness and playing music")
        
        # Use immediate brightness setting for responsive behavior
        logger.info(f"Setting brightness to {config.NORMAL_BRIGHTNESS}%")
        self.brightness_controller.set_brightness(config.NORMAL_BRIGHTNESS)
        logger.info(f"Brightness set to {config.NORMAL_BRIGHTNESS}%")
        
        # Start music
        self.spotify_controller.play_music()
        
        # Prevent system sleep while user is active
        self.system_controller.prevent_sleep()
        
        self.user_absent_start = None
    
    def handle_slouching(self):
        """Handle slouching state - Windows optimized"""
        logger.info("Slouching detected - Setting minimum brightness and pausing music")
        
        # Set brightness to configured slouching level (from config)
        logger.info(f"Setting brightness to {config.SLOUCHING_BRIGHTNESS}%")
        self.brightness_controller.set_brightness(config.SLOUCHING_BRIGHTNESS)
        logger.info(f"Brightness set to {config.SLOUCHING_BRIGHTNESS}%")
        
        # Pause music
        self.spotify_controller.pause_music()
        
        # Allow system to sleep (remove sleep prevention)
        self.system_controller.allow_sleep()
        
        self.user_absent_start = None
    
    def handle_user_absent(self):
        """Handle user absent state - Windows optimized"""
        # This function is now guarded by a lock to prevent race conditions
        with self.state_lock:
            logger.info("User absent detected")
            
            # Check if we're in the 10-second grace period after monitoring started
            if self.monitoring_start_time:
                grace_period_elapsed = (datetime.now() - self.monitoring_start_time).total_seconds()
                if grace_period_elapsed < 10:
                    logger.debug(f"Grace period active ({grace_period_elapsed:.1f}s / 10s), skipping sleep check")
                    return
            
            if self.user_absent_start is None:
                self.user_absent_start = datetime.now()
                # Set brightness to a dim level immediately instead of fading
                self.brightness_controller.set_brightness(30)
                logger.info("User absent - brightness dimmed to 30%")
            
            # Check if user has been absent for too long (3 seconds for testing)
            if self.user_absent_start is not None:  # Safety check
                time_absent = (datetime.now() - self.user_absent_start).total_seconds()
                logger.debug(f"User absent for {time_absent:.1f} seconds")
                
                if time_absent >= 3:  # 3 seconds for testing as requested
                    logger.info("User absent for 3+ seconds - Putting Windows system to sleep")
                    
                    # Set brightness to 0 before sleep
                    self.brightness_controller.set_brightness(0)
                    
                    # Put system to sleep
                    self.system_controller.sleep_system()

                    # Trigger application shutdown immediately after sleep
                    if self.shutdown_callback:
                        logger.info("System put to sleep. Shutting down application immediately.")
                        # Stop the detector loop to prevent further processing
                        self.running = False
                        # Trigger shutdown callback
                        threading.Thread(target=self.shutdown_callback, daemon=True).start()
    
    def run_detection_loop(self):
        """Main detection loop"""
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    continue
                
                # Detect posture
                detected_state = self.detect_posture(frame)
                self.handle_state_change(detected_state)
                
                # Update last detection time
                self.last_detection_time = datetime.now()
                
                # Convert frame to black and white for display
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Add status text overlay on the black and white frame
                status_text = f"State: {detected_state.replace('_', ' ').title()}"
                cv2.putText(gray_frame, status_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
                # Display black and white frame
                cv2.imshow('Slouching Detector - B&W', gray_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # Wait before next detection
                time.sleep(config.DETECTION_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                time.sleep(1)
    
    def start(self):
        """Start the slouching detector"""
        logger.info("Starting Slouching Detector...")
        
        # Initialize components
        if not self.initialize_roboflow():
            logger.error("Failed to initialize Roboflow")
            return False
        
        if not self.initialize_camera():
            logger.error("Failed to initialize camera")
            return False
        
        # Initialize Spotify
        self.spotify_controller.initialize()
        
        # Start detection
        self.running = True
        # Set monitoring start time for grace period
        self.monitoring_start_time = datetime.now()
        logger.info("Monitoring started - 10-second grace period active before sleep logic")
        
        try:
            self.run_detection_loop()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the detector and cleanup"""
        logger.info("Stopping Slouching Detector...")
        self.running = False
        
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        
        # Restore normal brightness
        self.brightness_controller.set_brightness(config.NORMAL_BRIGHTNESS)

if __name__ == "__main__":
    detector = SlouchingDetector()
    detector.start()
