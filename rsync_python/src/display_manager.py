import threading
import time
import sys

from rsync_python.src.shutdown_handler import ShutdownHandler

class DisplayManager:
    """ """
    
    def __init__(self, amount_of_transfers):
        self.lines = [""] * amount_of_transfers
        display_thread = threading.Thread(target=self._update_display)
        display_thread.daemon = True
        self._thread = display_thread
        self.display_lock = threading.Lock()
        self._stop = threading.Event()
        self._updated = False
        self._update_interval = 0.5

    def start(self):
        self._thread.start()

    def stop(self):
        if self._updated:
            time.sleep(self._update_interval)
        self._stop.set()
        self._thread.join()

    def update_lines(self, line_number, status):
        self.lines[line_number] = status
        self._updated = True
        
    def _update_display(self):
        """Update the terminal display with transfer progress"""
        # Initial setup - print empty lines for each transfer
        for _ in range(len(self.lines)):
            print()
        
        # Update loop
        while not self._stop.is_set():
            if ShutdownHandler().is_set():
                # self.print_progress()
                break
            self.print_progress()
            self._updated = False
                    
            # Wait before next update
            time.sleep(self._update_interval)

    def print_progress(self):
        with self.display_lock:
                # Move cursor to beginning
                sys.stdout.write("\033[F" * len(self.lines))
                
                # Print status for each transfer
                for line in self.lines:
                    # Clear line and print status
                    sys.stdout.write("\033[K" + line + "\n")
                
                sys.stdout.flush()