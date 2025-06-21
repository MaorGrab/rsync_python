import threading
import sys
from typing import List

from rsync_python.src.transfer import Transfer
from rsync_python.src.display_manager import DisplayManager
from rsync_python.utils.transfer_status import TransferStatus
from rsync_python.utils.optimal_worker_count import recommend_worker_count
from rsync_python.utils.shutdown_handler import ShutdownHandler

class TransferManager:
    """Manages concurrent execution of multiple rsync transfers."""
    
    def __init__(self, worker_count: int = 0) -> None:
        self.transfers = []
        self.worker_count = worker_count or recommend_worker_count()
        self.sem = threading.Semaphore(self.worker_count)
        self.statuses = []  # transfer statuses
        
    def add_transfer(self, transfer: Transfer) -> None:
        """Add a transfer to the execution queue."""
        self.transfers.append(transfer)

    def _worker_wrapper(self, transfer: Transfer) -> None:
        """Thread target: run transfer with semaphore and shutdown checks."""
        with self.sem:
            if ShutdownHandler().is_set():
                transfer.status = TransferStatus.CANCELLED
                return
            try:
                transfer.run()
            except Exception as e:
                transfer.error = f"Transfer error: {e}"
                transfer.update_status()

    def _start_workers(self) -> List[threading.Thread]:
        """Start worker threads for all transfers."""
        threads = []
        for transfer in self.transfers:
            thread = threading.Thread(target=self._worker_wrapper, args=(transfer,))
            # thread.daemon = True
            thread.start()
            threads.append(thread)
        return threads
    
    def _wait_for_threads(self, threads: List[threading.Thread]) -> None:
        """Join all worker threads with responsive timeout."""
        for thread in threads:
            while thread.is_alive():
                thread.join(timeout=1)
    
    def _poll_and_update_display(self, display: DisplayManager) -> None:
        """Continuously update display until all transfers complete or SIGINT recieved."""
        while True:
            if self._all_done or ShutdownHandler().is_set():
                break
            self._update_display(display)
            self._update_transfer_statistics()

    def _update_display(self, display: DisplayManager) -> None:
        """Update display with current status of all transfers."""
        for idx, t in enumerate(self.transfers):
            try:
                line = t.get_status_line()
            except Exception as e:
                line = f"{t.name}: ERROR fetching status: {e}"
            display.update_line(idx, line)

    def _update_transfer_statistics(self) -> None:
        """Update internal status tracking."""
        self.statuses = [transfer.status for transfer in self.transfers]

    def run_all(self) -> None:
        """Execute all transfers with real-time progress display."""
        threads = self._start_workers()
        display = DisplayManager(len(self.transfers))
        display.start()
        try:
            # Poll transfers and update display until done or shutdown
            self._poll_and_update_display(display)
        except Exception as e:
            sys.stderr.write(f"Unexpected error in polling: {e}\n")
        finally:
            self._wait_for_threads(threads)  # Wait for worker threads to finish
            self._update_display(display)  # Final display update
            self._update_transfer_statistics()
            display.stop(self.statuses)

    @property
    def _all_done(self) -> bool:
        """Check if all transfers have completed execution."""
        # RUNNING is 0 (Falsie)
        return all(transfer.status for transfer in self.transfers)
