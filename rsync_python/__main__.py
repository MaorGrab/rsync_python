from rsync_python.src.transfer import Transfer
from rsync_python.src.transfer_manager import TransferManager
from rsync_python.src.shutdown_handler import ShutdownHandler
from rsync_python.src.parse_args import parse_args, get_rsync_options


def main():
    """Main entry point for the transfer tool"""
    args = parse_args()
    rsync_options = get_rsync_options(args)  # Build rsync options

    shutdown_handler = ShutdownHandler()
    shutdown_handler.start()
    
    # Create transfer manager
    manager = TransferManager(max_workers=args.parallel)
    
    # Add transfers
    for source in args.sources:
        transfer = Transfer(
            source=source,
            dest=args.destination,
            options=rsync_options,
        )
        manager.add_transfer(transfer)
    
    # Run all transfers
    print(f"Starting {len(args.sources)} transfers with {args.parallel} workers...")
    try:
        manager.run_all()
    except Exception as e:
        print(f'Exception: {e}')
    finally:
        shutdown_handler.stop()
        print('cleanup code..')


if __name__ == "__main__":
    main()
