import threading
import signal
import sys

class ShutdownHandler:
    """
    Encapsulates a threading.Event triggered by SIGINT (Ctrl+C).
    Installs a SIGINT handler to set the event when Ctrl+C is received.
    Designed for single-instance use in a process.
    """
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        # If singleton desired, ensure only one instance is created
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Using singleton __new__, __init__ may be called multiple times;
        # guard initialization of attributes
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.shutdown_event = threading.Event()
        self._orig_handler = None
        self._initialized = True

    def start(self):
        """Install the SIGINT handler to trigger shutdown_event."""
        # Save original handler once
        if self._orig_handler is None:
            self._orig_handler = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, self._handle_sigint)

    def stop(self):
        self.shutdown_event.set()
        self.restore_handler()

    def restore_handler(self):
        """Restore the original SIGINT handler."""
        if self._orig_handler is not None:
            signal.signal(signal.SIGINT, self._orig_handler)
            self._orig_handler = None

    def _handle_sigint(self, signum, frame):
        """Internal SIGINT handler: sets shutdown_event."""
        sys.stderr.write("\nSIGINT received. Shutting down...\n")
        # Setting the event allows worker threads to detect shutdown.
        self.shutdown_event.set()
        # Note: not invoking external callbacks here.

    def is_set(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_event.is_set()

    def wait(self, timeout=None) -> bool:
        """
        Wait until shutdown_event is set or timeout occurs.
        Returns True if event is set, False if timeout elapsed.
        """
        return self.shutdown_event.wait(timeout)
