import subprocess
import os

from rsync_python.utils.shutdown_handler import ShutdownHandler
from rsync_python.utils.progress import Progress
from rsync_python.utils.transfer_status import TransferStatus


class Transfer:
    """Class to manage a single rsync transfer with progress monitoring"""
    
    def __init__(self, source, dest, options=None, name=None):
        self.source = source
        self.dest = dest
        self.options = options or []
        self.name = name or os.path.basename(os.path.normpath(source))
        self.progress = Progress(self.name)
        self._is_completed = False
        self._error = None
        self._process = None
        self.status = None
        
    def run(self):
        """Execute the rsync transfer and monitor progress"""
            
        # Build the command
        cmd = ["rsync", "-a", "--info=progress2"] + self.options + [self.source, self.dest]
        
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            self.status = TransferStatus.RUNNING

            # Monitor progress in real-time
            while self._process.poll() is None:
                line = self._process.stdout.readline()
                self.progress.update_from_line(line)
            
            # Check process status
            if ShutdownHandler().is_set():
                self.status = TransferStatus.CANCELLED
            elif self._process.returncode != 0:
                self._error = self._process.stderr.read()
            else:
                self._is_completed = True
                self.progress.set_complete()

        except Exception as e:
            self._error = str(e)
        
        finally:
            self.update_status()
            self.terminate()
        
    def terminate(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def get_status_line(self):
        return self.progress.status_line(self._error)
    
    def update_status(self):
        if self._is_completed:
            self.status = TransferStatus.COMPLETED
        elif self._error:
            self.status = TransferStatus.FAILED
        elif ShutdownHandler().is_set():
            self.status = TransferStatus.CANCELLED
