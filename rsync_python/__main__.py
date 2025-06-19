import argparse
import os

from rsync_python.src.transfer import Transfer
from rsync_python.src.transfer_manager import TransferManager
from rsync_python.src.shutdown_handler import ShutdownHandler

def main():
    """Main entry point for the transfer tool"""
    parser = argparse.ArgumentParser(
        description='Transfer files/folders using rsync with progress display'
    )
    
    # Required arguments
    parser.add_argument('sources', nargs='+', help='Source paths to transfer')
    parser.add_argument('destination', help='Destination path')
    
    # Optional arguments
    parser.add_argument('--parallel', type=int, default=3, 
                        help='Number of parallel transfers (default: 3)')
    parser.add_argument('--bwlimit', type=int, 
                        help='Bandwidth limit in KB/s')
    parser.add_argument('--archive', action='store_true', 
                        help='Use archive mode (-a)')
    
    args = parser.parse_args()

    shutdown_handler = ShutdownHandler()
    shutdown_handler.start()
    
    # Build rsync options
    rsync_options = []
    if args.archive:
        rsync_options.append("--archive")
    if args.bwlimit:
        rsync_options.append(f"--bwlimit={args.bwlimit}")
    
    # Create transfer manager
    manager = TransferManager(max_workers=args.parallel)
    
    # Add transfers
    for source in args.sources:
        transfer = Transfer(
            source=source,
            dest=args.destination,
            options=rsync_options,
            name=os.path.basename(source)
        )
        manager.add_transfer(transfer)
    
    # Run all transfers
    print(f"Starting {len(args.sources)} transfers with {args.parallel} workers...")
    try:
        manager.run_all()
    except KeyboardInterrupt:
        print('broke')
    except Exception as e:
        print(f'Exception: {e}')
    finally:
        shutdown_handler.stop()
        print('cleanup code..')


if __name__ == "__main__":
    main()
