import argparse


def parse_args() -> None:
    parser = argparse.ArgumentParser(
        description='Transfer files/folders using rsync with progress display'
    )
    
    # Required arguments
    parser.add_argument('sources', nargs='+', help='Source paths to transfer')
    parser.add_argument('destination', help='Destination path')
    
    # Optional arguments
    parser.add_argument('--parallel', type=int, default=3, 
                        help='Number of parallel transfers (default: 3)')
    parser.add_argument('--partial', action='store_true',
                        help='Save partial transfer files if transfer is interrupted')
    parser.add_argument('--bwlimit', type=int, 
                        help='Bandwidth limit in KB/s')
    
    args = parser.parse_args()
    return args

def get_rsync_options(args: argparse) -> list:
    rsync_options = []
    if args.partial:
        rsync_options.append("--partial")
        rsync_options.append("--inplace")
    if args.bwlimit:
        rsync_options.append(f"--bwlimit={args.bwlimit}")
    return rsync_options
