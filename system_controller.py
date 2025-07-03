import os
import subprocess
import logging
import ctypes
from ctypes import wintypes
import platform

logger = logging.getLogger(__name__)

# Windows API constants
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

class SystemController:
    def __init__(self):
        """Initialize Windows-specific system controller"""
        self.system = "Windows"  # Add system identifier for tests
        self.kernel32 = ctypes.windll.kernel32
        self.user32 = ctypes.windll.user32
        self.powrprof = ctypes.windll.powrprof
        
    def sleep_system(self):
        """Put Windows system to sleep"""
        try:
            # Use Windows API to suspend system
            result = self.powrprof.SetSuspendState(0, 1, 0)
            if result:
                logger.info("Windows system going to sleep")
                return True
            else:
                logger.error("Failed to put Windows system to sleep")
                return False
            
        except Exception as e:
            logger.error(f"Error putting Windows system to sleep: {e}")
            # Fallback to command line method
            try:
                subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
                logger.info("Windows system going to sleep (fallback method)")
                return True
            except subprocess.CalledProcessError as fallback_e:
                logger.error(f"Fallback sleep method also failed: {fallback_e}")
                return False
    
    def lock_system(self):
        """Lock Windows system"""
        try:
            result = self.user32.LockWorkStation()
            if result:
                logger.info("Windows system locked")
                return True
            else:
                logger.error("Failed to lock Windows system")
                return False
            
        except Exception as e:
            logger.error(f"Error locking Windows system: {e}")
            return False
    
    def prevent_sleep(self):
        """Prevent Windows system from going to sleep"""
        try:
            # Use SetThreadExecutionState to prevent sleep
            result = self.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            if result:
                logger.info("Windows sleep prevention activated")
                return True
            else:
                logger.error("Failed to prevent Windows sleep")
                return False
                
        except Exception as e:
            logger.error(f"Error preventing Windows sleep: {e}")
            return False
    
    def allow_sleep(self):
        """Allow Windows system to sleep again"""
        try:
            result = self.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            if result:
                logger.info("Windows sleep prevention deactivated")
                return True
            else:
                logger.error("Failed to allow Windows sleep")
                return False
                
        except Exception as e:
            logger.error(f"Error allowing Windows sleep: {e}")
            return False
    
    def set_monitor_power(self, power_on=True):
        """Turn monitor on/off"""
        try:
            # -1 = turn off, 2 = turn on
            power_state = 2 if power_on else -1
            result = self.user32.SendMessageW(
                0xFFFF,  # HWND_BROADCAST
                0x0112,  # WM_SYSCOMMAND
                0xF170,  # SC_MONITORPOWER
                power_state
            )
            action = "on" if power_on else "off"
            logger.info(f"Windows monitor turned {action}")
            return True
            
        except Exception as e:
            logger.error(f"Error controlling Windows monitor: {e}")
            return False

def is_windows():
    """Check if the operating system is Windows."""
    return platform.system() == "Windows"

def is_mac():
    """Check if the operating system is macOS."""
    return platform.system() == "Darwin"

def is_linux():
    """Check if the operating system is Linux."""
    return platform.system() == "Linux"

def run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Output: {e.stderr.strip()}")
        return None
