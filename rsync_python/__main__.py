from rsync_python.core.transfer import Transfer
from rsync_python.core.transfer_manager import TransferManager
from rsync_python.utils.shutdown_handler import ShutdownHandler
from rsync_python.cli.parse_args import parse_args, get_rsync_options


def main() -> None:
    """Main entry point for the transfer tool"""
    args = parse_args()
    rsync_options = get_rsync_options(args)  # Build rsync options

    shutdown_handler = ShutdownHandler()
    shutdown_handler.start()

    # Create transfer manager
    manager = TransferManager(worker_count=args.parallel)

    # Add transfers
    for source in args.sources:
        transfer = Transfer(
            source=source,
            dest=args.destination,
            options=rsync_options,
        )
        manager.add_transfer(transfer)

    # Run all transfers
    print(f"Starting {len(args.sources)} transfers with {manager.worker_count} workers...")
    try:
        manager.run_all()
    except Exception as e:  # pylint: disable=W0718  #  raise on any exception
        print(f'Exception: {e}')
    finally:
        shutdown_handler.stop()

if __name__ == "__main__":
    main()
