import subprocess
import re
import os

from rsync_python.src.shutdown_handler import ShutdownHandler


class Transfer:
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
            if ShutdownHandler().is_set():
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
                if ShutdownHandler().is_set():
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