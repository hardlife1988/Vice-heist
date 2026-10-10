"""Supported math entry point: generate a full release, including real books."""
import sys
from build_stake_bundle import main
if __name__=='__main__':
    if '--release' not in sys.argv:sys.argv.append('--release')
    main()
