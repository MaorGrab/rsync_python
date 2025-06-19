import re

class Progress:
    """Holds progress-related state for a transfer."""
    def __init__(self, name):
        self.name = name
        self.progress = 0       # percentage 0–100
        self.transfer_rate = "" # e.g., "1.2MB/s"
        self.eta = ""           # e.g., "00:01:23"

    def set_complete(self):
        self.progress = 100

    def update_from_line(self, line):
        """Parse rsync output line to update progress state."""
        if not line:
            return
        pct = re.search(r'(\d+)%', line)
        if pct: self.progress = int(pct.group(1))

        rate = re.search(r'(\d+\.\d+\w?B/s)', line)
        if rate: self.transfer_rate = rate.group(1)

        eta = re.search(r'(\d+:\d+:\d+)', line)
        if eta: self.eta = eta.group(1)

    def status_line(self, error=None):
        if error:
            return f"{self.name}: ERROR - {error}"
        if self.progress == 100:
            return f"{self.name}: Completed (100%)"
        bar_width = 20
        filled = int(self.progress / 100 * bar_width)
        bar = '█' * filled + '░' * (bar_width - filled)
        s = f"{self.name}: [{bar}] {self.progress}%"
        if self.transfer_rate:
            s += f" {self.transfer_rate}"
        if self.eta:
            s += f" ETA: {self.eta}"
        return s
