import re

from rsync_python.configurations import constants


class Progress:
    """Tracks progress state for a single transfer."""
    def __init__(self, name: str) -> None:
        self.name = name
        self.percentage = 0
        self.transfer_rate = ""
        self.eta = ""

    def set_complete(self) -> None:
        """Mark progress as 100% complete."""
        self.percentage = 100

    @property
    def is_complete(self) -> bool:
        """Check progress is at 100%"""
        return self.percentage == 100

    def update_from_line(self, line: str) -> None:
        """Update progress fields by parsing an rsync output line."""
        if not line:
            return
        if prcnt := re.search(r'(\d+)%', line):
            self.percentage = int(prcnt.group(1))
        if rate := re.search(r'(\d+\.\d+\w?B/s)', line):
            self.transfer_rate = rate.group(1)
        if eta := re.search(r'(\d+:\d+:\d+)', line):
            self.eta = eta.group(1)

    def status_line(self, error: str = '') -> str:
        """Return a formatted status line for display."""
        if error:
            return f"{self.name}: ERROR - {error}"
        if self.percentage == 100:
            return f"{self.name}: Completed (100%)"
        status = f"{self.name}: [{self._progress_bar}] {self.percentage}%"
        if self.transfer_rate:
            status += f" {self.transfer_rate}"
        if self.eta:
            status += f" ETA: {self.eta}"
        return status

    @property
    def _progress_bar(self) -> str:
        """Return a text progress bar string based on percentage."""
        bar_width = constants.PROGRESS_BAR_WIDTH
        filled = int(self.percentage / 100 * bar_width)
        progress_bar = constants.PROGRESS_BAR_FULL * filled
        progress_bar += constants.PROGRESS_BAR_EMPTY * (bar_width - filled)
        return progress_bar
