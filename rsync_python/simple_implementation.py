import subprocess
import threading
import re
import time
import sys
import os
import argparse
import signal
from concurrent.futures import ThreadPoolExecutor


shutdown_event = threading.Event()

def handle_sigint(signum, frame):
    print("\nSIGINT received. Shutting down...")
    shutdown_event.set()


class RsyncTransfer:
    """Class to manage a single rsync transfer with progress monitoring"""
    
    def __init__(self, source, dest, options=None, name=None):
        self.source = source
        self.dest = dest
        self.options = options or []
        self.name = name or os.path.basename(source)
        self.progress = 0
        self.transfer_rate = ""
        self.eta = ""
        self.is_completed = False
        self.error = None
        self.process = None
        
    def run(self):
        """Execute the rsync transfer and monitor progress"""
        # Ensure we have the progress option
        if "--info=progress2" not in self.options:
            self.options.append("--info=progress2")
            
        # Build the command
        cmd = ["rsync", "-a"] + self.options + [self.source, self.dest]
        
        try:
            if shutdown_event.is_set():
                return False
            # Start the rsync process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Monitor progress in real-time
            while self.process.poll() is None:
                if shutdown_event.is_set():
                    break
                line = self.process.stdout.readline()
                if line:
                    self._parse_progress(line.strip())
            
            # Check for errors
            if self.process.returncode != 0:
                self.error = self.process.stderr.read()
            else:
                self.is_completed = True
                self.progress = 100           
        except Exception as e:
            self.error = str(e)
        
        finally:
            self.terminate()
            return self.is_completed
        
    def terminate(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
    
    def _parse_progress(self, line):
        """Parse rsync progress output from --info=progress2"""
        # Extract percentage
        percentage_match = re.search(r'(\d+)%', line)
        if percentage_match:
            self.progress = int(percentage_match.group(1))
        
        # Extract transfer rate
        rate_match = re.search(r'(\d+\.\d+\w?B/s)', line)
        if rate_match:
            self.transfer_rate = rate_match.group(1)
            
        # Extract ETA
        eta_match = re.search(r'(\d+:\d+:\d+)', line)
        if eta_match:
            self.eta = eta_match.group(1)
    
    def get_status_line(self):
        """Get a formatted status line for display"""
        if self.error:
            return f"{self.name}: ERROR - {self.error}"
        elif self.is_completed:
            return f"{self.name}: Completed (100%)"
        else:
            # Create a progress bar
            bar_width = 20
            filled_width = int(self.progress / 100 * bar_width)
            bar = '█' * filled_width + '░' * (bar_width - filled_width)
            
            # Format the status line
            status = f"{self.name}: [{bar}] {self.progress}%"
            
            # Add transfer rate and ETA if available
            if self.transfer_rate:
                status += f" {self.transfer_rate}"
            if self.eta:
                status += f" ETA: {self.eta}"
                
            return status

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
            if shutdown_event.is_set():
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

def main():
    """Main entry point for the transfer tool"""
    parser = argparse.ArgumentParser(
        description='Transfer files/folders using rsync with progress display'
    )
    
    # Required arguments
    parser.add_argument('sources', nargs='+', help='Source paths to transfer')
    parser.add_argument('destination', help='Destination path')
    
    # Optional arguments
    parser.add_argument('--parallel', type=int, default=3, 
                        help='Number of parallel transfers (default: 3)')
    parser.add_argument('--bwlimit', type=int, 
                        help='Bandwidth limit in KB/s')
    parser.add_argument('--archive', action='store_true', 
                        help='Use archive mode (-a)')
    
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handle_sigint)
    
    # Build rsync options
    rsync_options = []
    if args.archive:
        rsync_options.append("--archive")
    if args.bwlimit:
        rsync_options.append(f"--bwlimit={args.bwlimit}")
    
    # Create transfer manager
    manager = TransferManager(max_workers=args.parallel)
    
    # Add transfers
    for source in args.sources:
        transfer = RsyncTransfer(
            source=source,
            dest=args.destination,
            options=rsync_options,
            name=os.path.basename(source)
        )
        manager.add_transfer(transfer)
    
    # Run all transfers
    print(f"Starting {len(args.sources)} transfers with {args.parallel} workers...")
    try:
        manager.run_all()
    except KeyboardInterrupt:
        print('broke')
    except Exception as e:
        print(f'Exception: {e}')
    finally:
        shutdown_event.set()
        print('cleanup code..')


if __name__ == "__main__":
    main()
