"""Serve packaged static demo on Replit. Real wagers use Stake RGS, never Flask."""
import os
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
if __name__=='__main__':
    root=Path(__file__).resolve().parent/'dist'
    if not (root/'game_config.json').exists():raise SystemExit('Run python math/build_stake_bundle.py first')
    server=ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','5000'))),partial(SimpleHTTPRequestHandler,directory=str(root)))
    print('Serving Vice Heist static bundle',flush=True)
    server.serve_forever()
