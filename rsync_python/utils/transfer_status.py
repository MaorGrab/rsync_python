from enum import IntEnum


class TransferStatus(IntEnum):
    """
    Represents the status of a transfer operation.

    Members:
        RUNNING (int): Transfer is currently in progress (value 0).
        COMPLETED (int): Transfer finished successfully (value 1).
        FAILED (int): Transfer ended with an error (value 2).
        CANCELLED (int): Transfer was cancelled before completion (value 3).
    """
    RUNNING = 0
    COMPLETED = 1
    FAILED = 2
    CANCELLED = 3
