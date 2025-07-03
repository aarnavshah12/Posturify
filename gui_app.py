"""
GUI version of the Slouching Detector
Provides a simple interface to start/stop monitoring
"""

import os
import sys
import time
import logging
import traceback
import gc
import tempfile
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sv_ttk
import cv2
import config
import threading

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from slouching_detector import SlouchingDetector, PostureState

class LogHandler(logging.Handler):
    """Custom logging handler to display logs in GUI"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        log_entry = self.format(record)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Schedule the GUI update in the main thread
        self.text_widget.after(0, self._append_log, f"[{timestamp}] {log_entry}")
    
    def _append_log(self, message):
        self.text_widget.insert(tk.END, message + "\n")
        self.text_widget.see(tk.END)

class SlouchingDetectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Slouching Detector")
        self.root.geometry("700x650") # Adjusted size for better fit
        self.root.resizable(False, False)
        
        # --- Color Palette (Nord Theme inspired) ---
        self.colors = {
            "background": "#2E3440",
            "panel": "#3B4252",
            "foreground": "#ECEFF4",
            "accent_blue": "#88C0D0",
            "accent_green": "#A3BE8C",
            "accent_red": "#BF616A",
            "accent_yellow": "#EBCB8B",
            "text_secondary": "#D8DEE9"
        }
        
        self.root.configure(bg=self.colors["background"])

        # --- Style Configuration ---
        s = ttk.Style()
        try:
            sv_ttk.set_theme("dark")
            # Override some sv_ttk styles for a custom look
            s.configure("TFrame", background=self.colors["background"])
            s.configure("TLabel", background=self.colors["background"], foreground=self.colors["foreground"])
            s.configure("TLabelFrame", background=self.colors["background"], bordercolor=self.colors["accent_blue"])
            s.configure("TLabelFrame.Label", background=self.colors["background"], foreground=self.colors["accent_blue"])
        except Exception:
            s.theme_use('clam')
            s.configure("TFrame", background=self.colors["background"])
            s.configure("TLabel", background=self.colors["background"], foreground=self.colors["foreground"])
            s.configure("TLabelFrame", background=self.colors["background"], bordercolor=self.colors["accent_blue"])
            s.configure("TLabelFrame.Label", background=self.colors["background"], foreground=self.colors["accent_blue"])
            s.configure("TButton", background=self.colors["panel"], foreground=self.colors["foreground"], borderwidth=1)
            s.map("TButton", background=[('active', self.colors["accent_blue"])])
        # Custom button styles
        s.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), foreground=self.colors["background"], background=self.colors["accent_green"])
        s.map("Accent.TButton", background=[('active', '#B9D7A8')]) # Lighter green on hover

        s.configure("Stop.TButton", font=("Segoe UI", 10, "bold"), foreground=self.colors["background"], background=self.colors["accent_red"])
        s.map("Stop.TButton", background=[('active', '#D1868E')]) # Lighter red on hover
            
        self.detector = None
        self.detector_thread = None
        self.is_running = False
        
        # Thread-safe variables for frame and status
        self.frame_lock = threading.Lock()
        self.latest_frame = None
        self.latest_status_text = "Initializing..."
        
        # Initialize the detector_lock
        self.detector_lock = threading.Lock()
        
        self.posture_history = []
        self.analysis_canvas = None
        
        self.setup_gui()
        self.setup_logging()
    
    def setup_gui(self):
        """Setup the GUI components with a modern, clean look"""
        # Define fonts for consistency
        TITLE_FONT = ("Segoe UI", 16, "bold")
        BODY_FONT = ("Segoe UI", 10)

        # --- Create a scrollable area ---
        self.main_canvas = tk.Canvas(self.root, bg=self.colors["background"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)

        self.scrollable_frame = ttk.Frame(self.main_canvas, style="TFrame")
        self.canvas_frame = self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.main_canvas.bind("<Configure>", self._on_canvas_configure)
        self.main_canvas.bind('<Enter>', self._bind_to_mousewheel)
        self.main_canvas.bind('<Leave>', self._unbind_from_mousewheel)

        # Main frame with padding, now inside the scrollable_frame
        main_frame = ttk.Frame(self.scrollable_frame, padding="15", style="TFrame")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Slouching Detector", font=TITLE_FONT, style="TLabel")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky=tk.W)
        
        # --- Container for the control panels ---
        controls_container = ttk.Frame(main_frame)
        controls_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        controls_container.columnconfigure(0, weight=1)
        controls_container.columnconfigure(1, weight=1)

        # --- Left Panel: Status & Main Controls ---
        left_panel = ttk.Frame(controls_container, style="TFrame")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_panel.columnconfigure(0, weight=1)

        # Status frame
        status_frame = ttk.LabelFrame(left_panel, text="Status", padding="10")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, text="App:", font=BODY_FONT).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.status_label = ttk.Label(status_frame, text="🟢 Ready", font=BODY_FONT, foreground=self.colors["accent_green"])
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="Posture:", font=BODY_FONT).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.current_state_label = ttk.Label(status_frame, text="Not monitoring", font=BODY_FONT, foreground=self.colors["text_secondary"])
        self.current_state_label.grid(row=1, column=1, sticky=tk.W)

        # Controls frame
        control_frame = ttk.LabelFrame(left_panel, text="Controls", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(0, weight=1)

        self.start_button = ttk.Button(control_frame, text="▶️ Start Monitoring", command=self.start_monitoring, style="Accent.TButton")
        self.start_button.pack(fill=tk.X, pady=2)
        
        self.stop_button = ttk.Button(control_frame, text="⏹️ Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED, style="Stop.TButton")
        self.stop_button.pack(fill=tk.X, pady=2)

        # --- Right Panel: Spotify ---
        right_panel = ttk.Frame(controls_container, style="TFrame")
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)

        # Spotify frame
        spotify_frame = ttk.LabelFrame(right_panel, text="Spotify", padding="10")
        spotify_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        spotify_frame.columnconfigure(0, weight=1)

        self.spotify_connect_button = ttk.Button(spotify_frame, text="🔗 Connect", command=self.connect_spotify)
        self.spotify_connect_button.pack(fill=tk.X, pady=2)

        self.spotify_status_label = ttk.Label(spotify_frame, text="Not connected", font=BODY_FONT, foreground=self.colors["text_secondary"])
        self.spotify_status_label.pack(fill=tk.X, pady=2)

        button_container = ttk.Frame(spotify_frame, style="TFrame")
        button_container.pack(fill=tk.X, pady=2)
        button_container.columnconfigure(0, weight=1)
        button_container.columnconfigure(1, weight=1)

        self.spotify_play_button = ttk.Button(button_container, text="▶️", command=self.spotify_play, state=tk.DISABLED)
        self.spotify_play_button.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 2))
        
        self.spotify_pause_button = ttk.Button(button_container, text="⏸️", command=self.spotify_pause, state=tk.DISABLED)
        self.spotify_pause_button.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(2, 0))

        self.current_track_label = ttk.Label(spotify_frame, text="Not connected", font=BODY_FONT, wraplength=180, justify=tk.CENTER, foreground=self.colors["text_secondary"])
        self.current_track_label.pack(fill=tk.X, pady=(5, 0))

        # --- Analysis Frame (initially hidden) ---
        self.analysis_frame = ttk.LabelFrame(main_frame, text="Posture Analysis", padding="10")
        # This frame will be populated with the graph later

        # --- Log frame below controls ---
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, width=60, height=10, font=BODY_FONT, 
                                                  background=self.colors["panel"], foreground=self.colors["text_secondary"],
                                                  bd=0, relief=tk.FLAT)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for responsive resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.scrollable_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1) # Make log expand vertically
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def _on_canvas_configure(self, event=None):
        """Adjust the width of the inner frame to the canvas width"""
        canvas_width = event.width
        self.main_canvas.itemconfig(self.canvas_frame, width=canvas_width)

    def _on_frame_configure(self, event=None):
        """Reset the scroll region to encompass the inner frame"""
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def _on_mousewheel(self, event):
        """Scroll the canvas with the mouse wheel"""
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _bind_to_mousewheel(self, event=None):
        """Bind mouse wheel scrolling"""
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_from_mousewheel(self, event=None):
        """Unbind mouse wheel scrolling"""
        self.main_canvas.unbind_all("<MouseWheel>")
    
    def setup_logging(self):
        """Setup logging to display in GUI"""
        # Create logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)  # Enable debug logging to see state changes
        
        # Clear existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add GUI handler
        gui_handler = LogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        self.logger.addHandler(gui_handler)
        
        # Initial log message
        self.logger.info("Slouching Detector GUI started (Windows Edition)")
        self.logger.info("Windows-specific optimizations enabled")
        
        # Check configuration status
        try:
            import config
            missing = config.validate_config()
            if missing:
                self.logger.warning(f"Missing configuration: {', '.join(missing)}")
                self.logger.info("Run setup.py to complete configuration")
            else:
                self.logger.info("Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Configuration error: {e}")
    
    def start_monitoring(self):
        """Start the slouching detector"""
        print("🔧 DEBUG: start_monitoring called")
        if self.is_running:
            print("🔧 DEBUG: Already running, returning")
            return
        
        # Clear previous analysis
        if self.analysis_canvas:
            self.analysis_canvas.get_tk_widget().destroy()
            self.analysis_canvas = None
        self.analysis_frame.grid_forget() # Hide the frame
        self.posture_history = [] # Reset history
        
        try:
            print("🔧 DEBUG: Setting status to Starting...")
            self.status_label.config(text="🟡 Initializing...", foreground=self.colors["accent_yellow"])
            self.start_button.config(state=tk.DISABLED)
            
            print("🔧 DEBUG: Creating detector instance...")
            # Create detector instance with a shutdown callback
            self.detector = SlouchingDetector(shutdown_callback=self._trigger_shutdown)
            print("🔧 DEBUG: Detector created successfully")
            
            print("🔧 DEBUG: Starting detector thread...")
            # Start detector in separate thread (like fast_gui.py)
            self.detector_thread = threading.Thread(target=self._run_detector, daemon=True)
            self.detector_thread.start()
            print("🔧 DEBUG: Thread started successfully")
            
            self.logger.info("Monitoring thread started...")
            
        except Exception as e:
            print(f"🔧 DEBUG: Exception in start_monitoring: {e}")
            traceback.print_exc()
            self.logger.error(f"Failed to start monitoring: {e}")
            self.status_label.config(text="❌ Failed to start", foreground=self.colors["accent_red"])
            self.start_button.config(state=tk.NORMAL)
            messagebox.showerror("Error", f"Failed to start monitoring:\n{e}")
    
    def _run_detector(self):
        """Run the detector (called in separate thread) - following fast_gui.py pattern"""
        print("🔧 DEBUG: _run_detector thread started")
        try:
            # Clear any potential caches first
            print("🔧 DEBUG: Clearing potential caches...")
            import gc
            gc.collect()
            
            # Try to clear Roboflow cache if it exists
            try:
                import os
                import tempfile
                import shutil
                
                # Common cache locations for Roboflow
                cache_dirs = [
                    os.path.expanduser("~/.roboflow"),
                    os.path.join(tempfile.gettempdir(), "roboflow"),
                    os.path.join(os.getcwd(), ".roboflow_cache")
                ]
                
                for cache_dir in cache_dirs:
                    if os.path.exists(cache_dir):
                        print(f"🔧 DEBUG: Found cache directory: {cache_dir}")
                        try:
                            # Don't actually delete, just list what's there
                            files = os.listdir(cache_dir)
                            print(f"🔧 DEBUG: Cache contains: {files}")
                        except Exception as e:
                            print(f"🔧 DEBUG: Could not list cache: {e}")
                
            except Exception as cache_error:
                print(f"🔧 DEBUG: Cache check failed: {cache_error}")
            
            print("🔧 DEBUG: Cache check completed")
            
            # Initialize components in thread (like fast_gui.py)
            print("🔧 DEBUG: About to initialize Roboflow...")
            try:
                # Re-enable Roboflow initialization
                if not self.detector.initialize_roboflow():
                    self.root.after(0, self._initialization_failed, "Roboflow initialization failed")
                    return
            except Exception as roboflow_error:
                print(f"🔧 DEBUG: Roboflow initialization crashed: {roboflow_error}")
                traceback.print_exc()
                self.root.after(0, self._initialization_failed, f"Roboflow error: {roboflow_error}")
                return
            print("🔧 DEBUG: Roboflow initialization successful")
            
            print("🔧 DEBUG: About to initialize camera...")
            if not self.detector.initialize_camera():
                print("🔧 DEBUG: Camera initialization failed")
                self.root.after(0, self._initialization_failed, "Camera initialization failed")
                return
            print("🔧 DEBUG: Camera initialization successful")
            
            print("🔧 DEBUG: About to initialize Spotify...")
            # Initialize Spotify (optional)
            self.detector.spotify_controller.initialize()
            print("🔧 DEBUG: Spotify initialization complete")
            
            print("🔧 DEBUG: Setting running states...")
            # Set running states
            self.is_running = True
            self.detector.running = True
            self.detector.monitoring_start_time = datetime.now()  # Set monitoring start time
            print("🔧 DEBUG: Running states set")
            
            print("🔧 DEBUG: About to call _initialization_successful...")
            # Update GUI to show we're running
            self.root.after(0, self._initialization_successful)
            print("🔧 DEBUG: _initialization_successful scheduled")
            
            # Schedule the first frame display
            self.root.after(10, self._display_frame)
            
            # Add a 5-second grace period before starting the main loop
            self.logger.info("Starting in 5 seconds... get ready!")
            time.sleep(5)
            self.logger.info("Grace period over. Starting detection.")
            self.logger.info("Sleep feature: System will sleep after 3 seconds of user absence (10s grace period from start)")

            # Create a window to display the camera feed
            cv2.namedWindow("Slouching Detector", cv2.WINDOW_NORMAL)

            # Processing loop with frame-based detection for better performance
            frame_counter = 0
            DETECTION_FRAME_INTERVAL = 3  # Process every 3rd frame
            self.logger.info(f"Posture detection will run on every {DETECTION_FRAME_INTERVAL}rd frame to optimize performance.")
            print("🔧 DEBUG: Entering main processing loop...")

            while self.detector.running and self.is_running:
                try:
                    ret, frame = self.detector.cap.read()
                    if not ret:
                        self.logger.warning("Failed to grab frame from camera, retrying...")
                        time.sleep(0.1)
                        continue

                    frame_counter += 1
                    processed_frame = frame
                    status_text = f"State: {self.detector.current_state.value if hasattr(self.detector.current_state, 'value') else self.detector.current_state}"

                    # Detect posture at frame intervals to reduce API calls and improve FPS
                    if frame_counter % DETECTION_FRAME_INTERVAL == 0:
                        # Add a lock or check to ensure self.detector is not None
                        with self.detector_lock:
                            if self.detector and self.is_running and self.detector.running:
                                self.logger.info("Running posture detection...")
                                detected_state = self.detector.detect_posture(frame)
                                
                                # ALWAYS process state change, even if it's the same
                                # This is crucial for the sleep logic to work properly
                                self.posture_history.append((datetime.now(), detected_state))
                                threading.Thread(target=self.detector.handle_state_change, args=(detected_state,), daemon=True).start()
                                
                                # Update status text based on new detection
                                status_text = f"State: {detected_state.value if hasattr(detected_state, 'value') else str(detected_state).replace('_', ' ').title()}"
                            else:
                                # If detector is gone, break the loop
                                break
                    
                    # Convert to grayscale for display
                    display_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
                    
                    # Add status text overlay
                    cv2.putText(display_frame, status_text, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

                    # Display the frame
                    cv2.imshow("Slouching Detector", display_frame)
                    cv2.waitKey(1) # Essential for imshow to work

                    # Safely update the shared frame
                    with self.frame_lock:
                        self.latest_frame = display_frame.copy()

                except Exception as e:
                    self.logger.error(f"Error in processing loop: {e}")
                    traceback.print_exc()
                    break
            
            print("🔧 DEBUG: Processing loop ended")
            self.logger.info("Processing loop ended")
                    
        except Exception as e:
            print(f"🔧 DEBUG: Exception in _run_detector: {e}")
            traceback.print_exc()
            self.logger.error(f"Critical error in monitoring thread: {e}")
            self.root.after(0, self._initialization_failed, f"Critical error: {e}")
        finally:
            print("🔧 DEBUG: _run_detector finally block")
            # Clean up resources in the thread that created them
            if self.detector and hasattr(self.detector, 'cap') and self.detector.cap:
                try:
                    print("🔧 DEBUG: Releasing camera from detector thread")
                    self.detector.cap.release()
                except Exception as e:
                    print(f"🔧 DEBUG: Error releasing camera: {e}")
            
            try:
                print("🔧 DEBUG: Destroying OpenCV windows from detector thread")
                cv2.destroyAllWindows()
                cv2.waitKey(1)  # Allow time for windows to close
            except Exception as e:
                print(f"🔧 DEBUG: Error destroying windows: {e}")
            
            print("🔧 DEBUG: Detector thread cleanup completed")
    
    def _display_frame(self):
        """This method is no longer needed as the display is handled in the processing loop."""
        pass

    def _update_state_display(self, state):
        """Update the current state display with Windows-specific styling"""
        try:
            state_text = f"State: {state.value}"
            
            # Update with fade effect
            self.current_state_label.config(text=state_text)
            self.current_state_label.after(500, lambda: self.current_state_label.config(foreground=self.colors["foreground"]))
            
        except Exception as e:
            self.logger.error(f"Error updating state display: {e}")

    def _initialization_successful(self):
        """Update GUI after successful initialization"""
        print("🔧 DEBUG: _initialization_successful called")
        self.status_label.config(text="🟢 Monitoring...", foreground=self.colors["accent_green"])
        self.stop_button.config(state=tk.NORMAL)
        self.logger.info("Initialization successful, monitoring started.")
        
    def _initialization_failed(self, reason):
        """Update GUI after failed initialization"""
        print(f"🔧 DEBUG: _initialization_failed called with reason: {reason}")
        self.logger.error(f"Error: {reason}")
        self.status_label.config(text=f"Error: {reason}", foreground=self.colors["accent_red"])
        self.start_button.config(state=tk.NORMAL)
        self.is_running = False
        if self.detector:
            self.detector.running = False
        messagebox.showerror("Initialization Failed", reason)
        self._cleanup_detector()

    def stop_monitoring(self):
        """Stop the slouching detector without blocking the GUI."""
        print("🔧 DEBUG: stop_monitoring called (non-blocking)")
        if not self.is_running and self.detector_thread is None:
            print("🔧 DEBUG: Already stopped, returning")
            return

        # Disable buttons to prevent multiple clicks
        self.stop_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.status_label.config(text="🟡 Stopping...", foreground=self.colors["accent_yellow"])
        
        # Signal the detector thread to stop
        self.is_running = False
        if self.detector:
            self.detector.running = False
        
        self.logger.info("⏹️ Stopping monitoring...")
        
        # Start polling to check when the thread has finished
        self.root.after(100, self._check_if_stopped)

    def _check_if_stopped(self):
        """Polls to see if the detector thread has finished."""
        if self.detector_thread and self.detector_thread.is_alive():
            # If still alive, check again in 100ms
            self.root.after(100, self._check_if_stopped)
        else:
            # Thread has finished, perform final cleanup in the main thread
            print("🔧 DEBUG: Detector thread has finished. Cleaning up.")
            self.detector_thread = None # Clear the thread reference
            self._cleanup_detector()
            
            self.status_label.config(text="🔴 Stopped", foreground=self.colors["accent_red"])
            self.current_state_label.config(text="Not monitoring", foreground=self.colors["text_secondary"])
            self.start_button.config(state=tk.NORMAL)
            # Keep stop button disabled
            
            self.logger.info("Monitoring stopped successfully.")
            print("🔧 DEBUG: stop_monitoring flow completed.")
            
            # Display posture analysis
            self._display_posture_analysis()
        
    def _cleanup_detector(self):
        """Release detector resources"""
        print("🔧 DEBUG: _cleanup_detector called")
        with self.detector_lock:
            if self.detector:
                # Camera and OpenCV cleanup is handled in the thread's finally block
                self.detector = None
                print("🔧 DEBUG: Detector instance cleaned up")
            else:
                print("🔧 DEBUG: Detector was already None")
            
            # Clear the latest frame
            with self.frame_lock:
                self.latest_frame = None
                print("🔧 DEBUG: Latest frame cleared")

    def _display_posture_analysis(self):
        """Calculate and display posture analysis graph"""
        if not self.posture_history:
            self.logger.info("No posture data to analyze.")
            return

        self.logger.info("Generating posture analysis...")

        proper_time = 0
        improper_time = 0

        for i in range(len(self.posture_history) - 1):
            start_time, state = self.posture_history[i]
            end_time, _ = self.posture_history[i+1]
            duration = (end_time - start_time).total_seconds()

            if state == PostureState.GOOD_POSTURE:
                proper_time += duration
            else: # Any other state is considered improper for simplicity
                improper_time += duration

        total_time = proper_time + improper_time
        if total_time == 0:
            self.logger.info("No sufficient posture data for analysis.")
            return

        proper_percent = (proper_time / total_time) * 100
        improper_percent = (improper_time / total_time) * 100

        # --- Create Matplotlib Pie Chart ---
        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
        fig.patch.set_facecolor(self.colors["background"])
        ax.set_facecolor(self.colors["background"])

        labels = [f'Proper ({proper_percent:.1f}%)', f'Improper ({improper_percent:.1f}%)']
        sizes = [proper_percent, improper_percent]
        colors = [self.colors["accent_green"], self.colors["accent_red"]]
        explode = (0.1, 0) if proper_percent > improper_percent else (0, 0.1)

        ax.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90,
               colors=colors, pctdistance=0.85,
               textprops={'color': self.colors["foreground"], 'fontweight': 'bold'})

        # Draw a circle at the center to make it a donut chart
        centre_circle = plt.Circle((0,0),0.70,fc=self.colors["background"])
        fig.gca().add_artist(centre_circle)

        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        plt.title("Posture Summary", color=self.colors["foreground"])

        # --- Embed in Tkinter ---
        self.analysis_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        if self.analysis_canvas:
            self.analysis_canvas.get_tk_widget().destroy()

        self.analysis_canvas = FigureCanvasTkAgg(fig, master=self.analysis_frame)
        self.analysis_canvas.draw()
        self.analysis_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.logger.info("Analysis complete.")

    def _trigger_shutdown(self):
        """Thread-safe method to trigger application shutdown after sleep."""
        self.logger.info("Shutdown triggered from detector. Closing application immediately.")
        # Set running to False to stop all processing
        self.is_running = False
        if self.detector:
            self.detector.running = False
        # Schedule immediate shutdown without delay
        self.root.after(0, self._force_close)

    def _update_brightness_display_safe(self):
        """Update brightness display in GUI safely (non-blocking)"""
        def _update_brightness():
            try:
                from brightness_controller import BrightnessController
                bc = BrightnessController()
                current = bc.get_current_brightness()
                # Schedule GUI update in main thread
                self.root.after(0, lambda: self.brightness_label.config(text=f"Brightness: {current}%"))
            except Exception as e:
                # Schedule GUI update in main thread
                self.root.after(0, lambda: self.brightness_label.config(text="Brightness: Unknown"))
        
        # Run brightness check in background thread to avoid blocking
        threading.Thread(target=_update_brightness, daemon=True).start()
    
    def _update_brightness_display(self):
        """Update brightness display in GUI"""
        try:
            from brightness_controller import BrightnessController
            bc = BrightnessController()
            current = bc.get_current_brightness()
            self.brightness_label.config(text=f"Brightness: {current}%")
        except Exception as e:
            self.brightness_label.config(text="Brightness: Unknown")

    def on_closing(self):
        """Handle window closing"""
        if self.is_running:
            self.stop_monitoring()
            # Give it a moment to stop
            self.root.after(1000, self._force_close)
        else:
            self.root.destroy()
    
    def _force_close(self):
        """Force close the application"""
        self.root.destroy()

    def connect_spotify(self):
        """Connect to Spotify using the provided redirect URL"""
        self.logger.info("Connecting to Spotify...")
        
        def _connect():
            try:
                # Initialize Spotify controller
                from spotify_controller import SpotifyController
                self.spotify_controller = SpotifyController()
                
                # This will now handle the full auth flow
                if self.spotify_controller.initialize():
                    user = self.spotify_controller.sp.current_user()
                    if user:
                        self.logger.info(f"Connected to Spotify as: {user['display_name']}")
                        self.root.after(0, self._spotify_connected)
                        self._update_current_track()
                    else:
                        self.logger.error("Failed to get user information after auth")
                else:
                    self.logger.error("Spotify connection failed or was cancelled.")
                    
            except Exception as e:
                self.logger.error(f"Failed to connect to Spotify: {e}")
                import traceback
                traceback.print_exc()
        
        # Run connection in background thread
        threading.Thread(target=_connect, daemon=True).start()
    
    def _spotify_connected(self):
        """Update GUI when Spotify is connected"""
        self.spotify_status_label.config(text="Connected", foreground=self.colors["accent_green"])
        self.spotify_play_button.config(state=tk.NORMAL)
        self.spotify_pause_button.config(state=tk.NORMAL)
        self.spotify_connect_button.config(text="✅ Connected", state=tk.DISABLED)
    
    def spotify_play(self):
        """Play music on Spotify"""
        if hasattr(self, 'spotify_controller') and self.spotify_controller.is_initialized:
            def _play():
                success = self.spotify_controller.play_music()
                if success:
                    self.root.after(100, self._update_current_track)
            threading.Thread(target=_play, daemon=True).start()
        else:
            self.logger.error("Spotify not connected")
    
    def spotify_pause(self):
        """Pause music on Spotify"""
        if hasattr(self, 'spotify_controller') and self.spotify_controller.is_initialized:
            def _pause():
                success = self.spotify_controller.pause_music()
                if success:
                    self.root.after(100, self._update_current_track)
            threading.Thread(target=_pause, daemon=True).start()
        else:
            self.logger.error("Spotify not connected")
    
    def _update_current_track(self):
        """Update the current track display"""
        if not hasattr(self, 'spotify_controller') or not self.spotify_controller.is_initialized:
            return
        
        def _get_current():
            try:
                current = self.spotify_controller.sp.current_playback()
                if current and current['item']:
                    track_name = current['item']['name']
                    artist_name = current['item']['artists'][0]['name']
                    is_playing = current['is_playing']
                    
                    status = "▶️" if is_playing else "⏸️"
                    text = f"{status} {track_name} by {artist_name}"
                    
                    self.root.after(0, lambda: self.current_track_label.config(text=text, foreground=self.colors["foreground"]))
                else:
                    self.root.after(0, lambda: self.current_track_label.config(text="No track playing", foreground=self.colors["text_secondary"]))
            except Exception as e:
                self.root.after(0, lambda: self.current_track_label.config(text="Error getting track info", foreground=self.colors["accent_red"]))
        
        threading.Thread(target=_get_current, daemon=True).start()

def main():
    root = tk.Tk()
    app = SlouchingDetectorGUI(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()
