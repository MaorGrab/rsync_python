import subprocess
import os

from rsync_python.src.shutdown_handler import ShutdownHandler
from rsync_python.src.progress import Progress


class Transfer:
    """Class to manage a single rsync transfer with progress monitoring"""
    
    def __init__(self, source, dest, options=None, name=None):
        self.source = source
        self.dest = dest
        self.options = options or []
        self.name = name or os.path.basename(os.path.normpath(source))
        self.progress = Progress(self.name)
        self.is_completed = False
        self.error = None
        self.process = None
        
    def run(self):
        """Execute the rsync transfer and monitor progress"""
            
        # Build the command
        cmd = ["rsync", "-a", "--info=progress2"] + self.options + [self.source, self.dest]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Monitor progress in real-time
            while self.process.poll() is None:
                line = self.process.stdout.readline()
                self.progress.update_from_line(line)
            
            # Check process status
            if ShutdownHandler().is_set():
                pass
            elif self.process.returncode != 0:
                self.error = self.process.stderr.read()
            else:
                self.is_completed = True
                self.progress.set_complete()
            return self.is_completed

        except Exception as e:
            self.error = str(e)
            return self.is_completed
        
        finally:
            self.terminate()
        
    def terminate(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def get_status_line(self):
        return self.progress.status_line(self.error)
