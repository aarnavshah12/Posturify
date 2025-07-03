import screen_brightness_control as sbc
import logging
import ctypes
from ctypes import wintypes
import time
import threading

logger = logging.getLogger(__name__)

class BrightnessController:
    def __init__(self):
        self.current_brightness = None
        self.monitors = []
        self.brightness_lock = threading.Lock()  # Add lock for thread safety
        self.discover_monitors()
        self.get_current_brightness()
    
    def discover_monitors(self):
        """Discover all available monitors on Windows"""
        try:
            self.monitors = sbc.list_monitors()
            if self.monitors:
                logger.info(f"Discovered {len(self.monitors)} monitor(s): {self.monitors}")
            else:
                logger.warning("No monitors discovered, using default methods")
        except Exception as e:
            logger.error(f"Failed to discover monitors: {e}")
            self.monitors = []
    
    def get_current_brightness(self):
        """Get current screen brightness"""
        try:
            if self.monitors:
                # Get brightness from first monitor
                brightness_values = sbc.get_brightness()
                if isinstance(brightness_values, list) and len(brightness_values) > 0:
                    self.current_brightness = brightness_values[0]
                else:
                    self.current_brightness = brightness_values
            else:
                # Fallback method
                self.current_brightness = sbc.get_brightness()
            
            logger.info(f"Current brightness: {self.current_brightness}%")
            return self.current_brightness
        except Exception as e:
            logger.error(f"Failed to get current brightness: {e}")
            return 100  # Default to full brightness
    
    def set_brightness(self, brightness_level):
        """Set screen brightness (0-100) on Windows"""
        with self.brightness_lock:  # Prevent concurrent brightness changes
            try:
                if brightness_level < 0:
                    brightness_level = 0
                elif brightness_level > 100:
                    brightness_level = 100
                
                logger.info(f"Setting brightness to {brightness_level}%")
                
                # Try setting brightness for all monitors
                if self.monitors:
                    for monitor in self.monitors:
                        try:
                            sbc.set_brightness(brightness_level, display=monitor)
                            logger.info(f"Set brightness to {brightness_level}% on monitor: {monitor}")
                        except Exception as monitor_error:
                            logger.warning(f"Failed to set brightness on monitor {monitor}: {monitor_error}")
                else:
                    # Fallback to general method
                    sbc.set_brightness(brightness_level)
                    logger.info(f"Set brightness to {brightness_level}% (general method)")
                
                self.current_brightness = brightness_level
                
                # Add small delay to ensure change takes effect
                time.sleep(0.1)
                return True
                
            except Exception as e:
                logger.error(f"Failed to set brightness to {brightness_level}%: {e}")
                # Try Windows WMI fallback
                return self._set_brightness_wmi(brightness_level)
    
    def _set_brightness_wmi(self, brightness_level):
        """Fallback method using Windows WMI"""
        try:
            import wmi
            c = wmi.WMI(namespace='wmi')
            methods = c.WmiMonitorBrightnessMethods()[0]
            methods.WmiSetBrightness(brightness_level, 0)
            logger.info(f"Set brightness to {brightness_level}% using WMI")
            return True
        except ImportError:
            logger.warning("WMI module not available for brightness fallback")
            return False
        except Exception as e:
            logger.error(f"WMI brightness fallback failed: {e}")
            return False
    
    def fade_brightness(self, target_brightness, duration=2.0, steps=20):
        """Gradually fade brightness to target level"""
        try:
            start_brightness = self.get_current_brightness()
            if start_brightness is None:
                start_brightness = 100
            
            step_size = (target_brightness - start_brightness) / steps
            step_duration = duration / steps
            
            for i in range(steps):
                current_step_brightness = start_brightness + (step_size * (i + 1))
                self.set_brightness(int(current_step_brightness))
                time.sleep(step_duration)
            
            # Ensure we end at exactly the target brightness
            self.set_brightness(target_brightness)
            logger.info(f"Faded brightness from {start_brightness}% to {target_brightness}%")
            return True
            
        except Exception as e:
            logger.error(f"Failed to fade brightness: {e}")
            # Fallback to direct setting
            return self.set_brightness(target_brightness)
    
    def restore_brightness(self):
        """Restore brightness to 100%"""
        return self.set_brightness(100)
    
    def dim_screen(self):
        """Quickly dim screen for slouching"""
        return self.set_brightness(20)
    
    def brighten_screen(self):
        """Quickly brighten screen for good posture"""
        return self.set_brightness(100)
