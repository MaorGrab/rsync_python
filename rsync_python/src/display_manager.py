import threading
import time
import sys
from collections import Counter
from typing import List

from rsync_python.configurations import constants
from rsync_python.utils.transfer_status import TransferStatus

class DisplayManager:
    """ """
    
    def __init__(self, amount_of_transfers: int) -> None:
        self._lines = [""] * amount_of_transfers
        self._thread = self._set_display_thread()
        self._display_lock = threading.Lock()
        self._stop_event = threading.Event()

    def _set_display_thread(self) -> threading.Thread:
        display_thread = threading.Thread(target=self._update_display)
        display_thread.daemon = True
        return display_thread

    def start(self) -> None:
        self._thread.start()

    def stop(self, statuses: List[TransferStatus]) -> None:
        self._print_progress()
        self._stop_event.set()
        self.print_summary(statuses)
        self._thread.join()

    def update_line(self, line_number: int, status_line: str) -> None:
        self._lines[line_number] = status_line
        
    def _update_display(self) -> None:
        """Update the terminal display with transfer progress"""
        for _ in range(len(self._lines)):  # Initial setup - print empty lines for each transfer
            print()
        while not self._stop_event.is_set():
            self._print_progress()
            time.sleep(constants.DISPLAY_UPDATE_INTERVAL)  # Wait before next update

    def _print_progress(self) -> None:
        with self._display_lock:
                # Move cursor to beginning of previous line
                sys.stdout.write(constants.CSI_PREV_LINE * len(self._lines))
                # Print status for each transfer
                for line in self._lines:
                    # Clear line and print status
                    sys.stdout.write(constants.CSI_ERASE_LINE + line + "\n")
                sys.stdout.flush()

    @staticmethod
    def print_summary(statuses: List[TransferStatus]) -> None:
        statuses_counter = Counter(statuses)
        print(
            f"\nSummary: {statuses_counter[TransferStatus.COMPLETED]} completed, "
            f"{statuses_counter[TransferStatus.FAILED]} failed, "
            f"{statuses_counter[TransferStatus.CANCELLED]} cancelled."
        )
