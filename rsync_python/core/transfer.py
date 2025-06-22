import subprocess
import os

from rsync_python.utils.progress import Progress
from rsync_python.utils.transfer_status import TransferStatus
from rsync_python.utils.shutdown_handler import ShutdownHandler


# pylint: disable=R1732
# pylint: disable=too-many-instance-attributes
class Transfer:
    """Manages a single rsync transfer with progress monitoring."""
    def __init__(self, source: str, dest: str, options: list = None, name: str = None) -> None:
        self.source = source
        self.dest = dest
        self.options = options or []
        self.name = name or os.path.basename(os.path.normpath(source))
        self.progress = Progress(self.name)
        self._error = None
        self._process = None
        self.status = None

    def run(self) -> None:
        """Execute the rsync transfer and update progress in real time."""
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
                self.progress.set_complete()

        except Exception as e:  # pylint: disable=W0718  #  raise on any exception
            self._error = str(e)

        finally:
            self.update_status()
            self.terminate()

    def terminate(self) -> None:
        """Terminate the rsync subprocess if running."""
        if self._process and self._process.poll() is None:
            self._process.stdout.close()
            self._process.stderr.close()
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

    def get_status_line(self) -> str:
        """Return a formatted status line for display."""
        return self.progress.status_line(self._error)

    def update_status(self) -> None:
        """Update the transfer status based on completion, errors or cancellation."""
        if self.progress.is_complete:
            self.status = TransferStatus.COMPLETED
        elif self._error:
            self.status = TransferStatus.FAILED
        elif ShutdownHandler().is_set():
            self.status = TransferStatus.CANCELLED
