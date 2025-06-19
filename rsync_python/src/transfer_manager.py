import threading
import time
import sys
from concurrent.futures import ThreadPoolExecutor

from rsync_python.src.shutdown_handler import ShutdownHandler

class TransferManager:
    """Class to manage multiple concurrent rsync transfers"""
    
    def __init__(self, max_workers=3):
        self.transfers = []
        self.max_workers = max_workers
        self.display_lock = threading.Lock()
        self.running = True
        
    def add_transfer(self, transfer):
        """Add a transfer to be managed"""
        self.transfers.append(transfer)
    
    def run_all(self):
        """Run all transfers concurrently with progress display"""
        # Start display thread
        display_thread = threading.Thread(target=self._update_display)
        display_thread.daemon = True
        display_thread.start()
        
        # Execute transfers using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all transfers
            futures = [executor.submit(transfer.run) for transfer in self.transfers]
            
            # Wait for all to complete
            try:
                for future in futures:
                    future.result()
            except Exception as e:
                print('exception is tranfermanager:', e)
            finally:
                print('tranfermanager finally')
                
        # Signal display thread to stop
        self.running = False
        display_thread.join(timeout=1.0)
        
        # Final display update
        print("\nAll transfers completed!")
    
    def _update_display(self):
        """Update the terminal display with transfer progress"""
        # Initial setup - print empty lines for each transfer
        for _ in range(len(self.transfers)):
            print("")
        
        # Update loop
        while self.running:
            if ShutdownHandler().is_set():
                break
            with self.display_lock:
                # Move cursor to beginning
                sys.stdout.write("\033[F" * len(self.transfers))
                
                # Print status for each transfer
                for transfer in self.transfers:
                    status = transfer.get_status_line()
                    # Clear line and print status
                    sys.stdout.write("\033[K" + status + "\n")
                
                sys.stdout.flush()
            
            # Check if all transfers are completed
            if all(t.is_completed or t.error for t in self.transfers):
                break
                    
            # Wait before next update
            time.sleep(0.5)
