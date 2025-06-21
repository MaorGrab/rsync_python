import threading
import sys
from typing import List

from rsync_python.src.transfer import Transfer
from rsync_python.src.display_manager import DisplayManager
from rsync_python.utils.transfer_status import TransferStatus
from rsync_python.utils.shutdown_handler import ShutdownHandler

class TransferManager:
    """Class to manage multiple concurrent rsync transfers"""
    
    def __init__(self, max_workers: int = 3) -> None:
        self.transfers = []
        self.sem = threading.Semaphore(max_workers)
        self.statuses = []
        
    def add_transfer(self, transfer: Transfer) -> None:
        """Add a transfer to be managed"""
        self.transfers.append(transfer)

    def _worker_wrapper(self, transfer: Transfer) -> None:
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
        """
        Start one thread per transfer, each running _worker_wrapper.
        Returns list of Thread objects.
        """
        threads = []
        for transfer in self.transfers:
            thread = threading.Thread(target=self._worker_wrapper, args=(transfer,))
            # thread.daemon = True
            thread.start()
            threads.append(thread)
        return threads
    
    def _wait_for_threads(self, threads: List[threading.Thread]) -> None:
        """
        Join all worker threads, but remain responsive by using timeout in join.
        """
        for thread in threads:
            while thread.is_alive():
                thread.join(timeout=1)
    
    def _poll_and_update_display(self, display: DisplayManager) -> None:
        """
        Poll each transfer's status and update the display.
        Loop until all transfers done or shutdown_event set.
        """
        while True:
            if self._all_done or ShutdownHandler().is_set():
                break
            self._update_display(display)
            self._update_transfer_statistics()

    def _update_display(self, display: DisplayManager) -> None:
        for idx, t in enumerate(self.transfers):
            try:
                line = t.get_status_line()
            except Exception as e:
                line = f"{t.name}: ERROR fetching status: {e}"
            display.update_line(idx, line)

    def _update_transfer_statistics(self) -> None:
        self.statuses = [transfer.status for transfer in self.transfers]

    def run_all(self) -> None:
        """Run all transfers concurrently with progress display"""
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
        # RUNNING is 0 (Falsie)
        return all(transfer.status for transfer in self.transfers)
