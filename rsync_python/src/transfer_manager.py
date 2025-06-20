import threading
import time
import sys
from concurrent.futures import ThreadPoolExecutor

from rsync_python.src.shutdown_handler import ShutdownHandler
from rsync_python.src.display_manager import DisplayManager

class TransferManager:
    """Class to manage multiple concurrent rsync transfers"""
    
    def __init__(self, max_workers=3):
        self.transfers = []
        # self.max_workers = max_workers
        self.sem = threading.Semaphore(max_workers)
        self.refresh_interval = 0.5
        self.summary = dict.fromkeys(["completed", "failed", "cancelled"], 0)
        # self.display_lock = threading.Lock()
        # self.running = True
        
    def add_transfer(self, transfer):
        """Add a transfer to be managed"""
        self.transfers.append(transfer)

    def _worker_wrapper(self, transfer):
        with self.sem:
            if ShutdownHandler().is_set():
                return
            try:
                transfer.run()
            except Exception as e:
                transfer.error = f"Transfer error: {e}"
                ShutdownHandler().shutdown_event.set()

    def _start_workers(self):
        """
        Start one thread per transfer, each running _worker_wrapper.
        Returns list of Thread objects.
        """
        threads = []
        for t in self.transfers:
            th = threading.Thread(target=self._worker_wrapper, args=(t,))
            # th.daemon = True
            th.start()
            threads.append(th)
        return threads
    

    def _poll_and_update_display(self, display):
        """
        Poll each transfer's status and update the display.
        Loop until all transfers done or shutdown_event set.
        """
        while True:
            if self._all_done or ShutdownHandler().is_set():
                self._update_transfer_statistics(t)
                break
            for idx, t in enumerate(self.transfers):
                try:
                    line = t.get_status_line()
                except Exception as e:
                    line = f"{t.name}: ERROR fetching status: {e}"
                display.update_lines(idx, line)
            self._update_transfer_statistics(t)

            # Wait, waking early on shutdown_event
            # ShutdownHandler().wait(self.refresh_interval)
            # Loop continues; if shutdown_event set, break condition triggers above

    def _update_transfer_statistics(self, transfer):
        self.summary = dict.fromkeys(["completed", "failed", "cancelled"], 0)
        for transfer in self.transfers:
            if transfer.is_completed:
                self.summary['completed'] += 1
            elif transfer.error:
                self.summary['failed'] += 1
            elif ShutdownHandler().is_set():
                self.summary['cancelled'] += 1

    @property
    def _all_done(self):
        return sum(self.summary.values()) == len(self.transfers)

    def _wait_for_threads(self, threads):
        """
        Join all worker threads, but remain responsive by using timeout in join.
        """
        for th in threads:
            while th.is_alive():
                th.join(timeout=1)

    def _print_summary(self):
        print(f"\nSummary: {self.summary['completed']} completed, "
              f"{self.summary['failed']} failed, {self.summary['cancelled']} cancelled.")

    def run_all(self):
        """Run all transfers concurrently with progress display"""
        threads = self._start_workers()
        # Main thread: poll status and update display until all threads finish or shutdown
        display = DisplayManager(len(self.transfers))
        display.start()
        
        try:
            # Poll transfers and update display until done or shutdown
            self._poll_and_update_display(display)
        except Exception as e:
            # Unexpected error in polling
            sys.stderr.write(f"Exception in display loop: {e}\n")
        finally:
            # Wait for worker threads to finish
            self._wait_for_threads(threads)
            # Final display update
            for idx, t in enumerate(self.transfers):
                try:
                    line = t.get_status_line()
                    display.update_lines(idx, line)
                except Exception as e:
                    print(f'Couldn\'t get status line: {e}')
            # time.sleep(1)
        display.stop()
        self._print_summary()
