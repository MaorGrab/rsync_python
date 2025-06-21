import re

from rsync_python.configurations import constants

class Progress:
    """Holds progress-related state for a transfer."""
    def __init__(self, name: str) -> None:
        self.name = name
        self.percentage = 0
        self.transfer_rate = ""
        self.eta = ""

    def set_complete(self) -> None:
        self.percentage = 100

    def update_from_line(self, line: str) -> None:
        """Parse rsync output line to update progress state."""
        if not line:
            return
        prcnt = re.search(r'(\d+)%', line)
        if prcnt: self.percentage = int(prcnt.group(1))

        rate = re.search(r'(\d+\.\d+\w?B/s)', line)
        if rate: self.transfer_rate = rate.group(1)

        eta = re.search(r'(\d+:\d+:\d+)', line)
        if eta: self.eta = eta.group(1)

    def status_line(self, error: str = '') -> str:
        if error:
            return f"{self.name}: ERROR - {error}"
        if self.percentage == 100:
            return f"{self.name}: Completed (100%)"
        status = f"{self.name}: [{self.bar}] {self.percentage}%"
        if self.transfer_rate:
            status += f" {self.transfer_rate}"
        if self.eta:
            status += f" ETA: {self.eta}"
        return status
    
    @property
    def bar(self) -> str:
        bar_width = constants.PROGRESS_BAR_WIDTH
        filled = int(self.percentage / 100 * bar_width)
        bar = constants.PROGRESS_BAR_FULL * filled
        bar += constants.PROGRESS_BAR_EMPTY * (bar_width - filled)
        return bar
