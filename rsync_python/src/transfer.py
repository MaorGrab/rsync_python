import subprocess
import re
import os

from rsync_python.src.shutdown_handler import ShutdownHandler
from rsync_python.src.progress import Progress


class Transfer:
    """Class to manage a single rsync transfer with progress monitoring"""
    
    def __init__(self, source, dest, options=None, name=None):
        self.source = source
        self.dest = dest
        self.options = options or []
        self.name = name or os.path.basename(source)
        self.progress = Progress(name)
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
                self.progress.update_from_line(line)
            
            # Check for errors
            if self.process.returncode != 0:
                self.error = self.process.stderr.read()
            else:
                self.is_completed = True
                self.progress.set_complete()
        except Exception as e:
            self.error = str(e)
        
        finally:
            self.terminate()
            return self.is_completed
        
    def terminate(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def get_status_line(self):
        return self.progress.status_line(self.error)
