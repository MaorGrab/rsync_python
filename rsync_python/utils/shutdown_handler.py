import threading
import signal

from rsync_python.configurations import constants


class ShutdownHandler:
    """
    Singleton class to handle graceful shutdown requests in a multi-threaded application.

    This class manages a threading.Event that is set when a SIGINT (Ctrl+C) is received,
    or when triggered manually. It installs a custom SIGINT handler that sets the event,
    allowing the main program and worker threads to check for shutdown requests and exit gracefully.

    Notes:
        - Only one instance of ShutdownHandler should be used per process (singleton pattern).
        - Call `start()` to install the SIGINT handler.
        - Call `trigger()` to trigger a SIGINT event.
        - Call `stop()` to trigger shutdown and restore the original SIGINT handler.
        - Use `is_set()` to check if shutdown has been requested.
    """
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> 'ShutdownHandler':
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.shutdown_event = threading.Event()
        self._orig_handler = None
        self._initialized = True

    def start(self) -> None:
        """Install the SIGINT handler to trigger shutdown_event."""
        # Save original handler once
        if self._orig_handler is None:
            self._orig_handler = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, self._handle_sigint)

    def trigger(self) -> None:
        """Set shutdown_event manually."""
        self.shutdown_event.set()

    def stop(self) -> None:
        """Set shutdown_event and restore original SIGINT handler."""
        self.trigger()
        self._restore_handler()

    def _restore_handler(self) -> None:
        """Restore the original SIGINT handler."""
        if self._orig_handler is not None:
            signal.signal(signal.SIGINT, self._orig_handler)
            self._orig_handler = None

    def _handle_sigint(self, signum, frame) -> None:
        """Internal SIGINT handler: sets shutdown_event."""
        print(constants.CSI_PREV_LINE)
        self.shutdown_event.set()

    def is_set(self) -> bool:
        """Return True if shutdown has been requested."""
        return self.shutdown_event.is_set()
