"""
StakeEngine provably fair integration for Vice Heist.

The provably fair algorithm:
  1. Server generates a random server_seed (kept secret until rotated).
  2. Server sends sha256(server_seed) to client BEFORE any bets.
  3. Client provides client_seed (can change between sessions).
  4. Each spin: nonce increments by 1.
  5. Spin entropy: HMAC-SHA256(key=server_seed, msg=f"{client_seed}:{nonce}")
  6. Player can verify after server_seed is revealed (on rotation / cashout).
"""

import hashlib
import hmac
import secrets
import json


def generate_server_seed() -> tuple[str, str]:
    """
    Generate a new server seed.

    Returns:
        (server_seed, server_seed_hash) — keep server_seed secret,
        show server_seed_hash to the player before bets start.
    """
    seed = secrets.token_hex(32)           # 256-bit random secret
    seed_hash = hashlib.sha256(seed.encode()).hexdigest()
    return seed, seed_hash


def get_server_seed_hash(server_seed: str) -> str:
    return hashlib.sha256(server_seed.encode()).hexdigest()


def generate_spin_bytes(server_seed: str, client_seed: str, nonce: int) -> bytes:
    """
    Generate the raw entropy bytes for a spin.
    Returns 32 bytes of HMAC-SHA256.
    """
    message = f"{client_seed}:{nonce}".encode()
    return hmac.new(server_seed.encode(), message, hashlib.sha256).digest()


def verify_spin(server_seed: str, client_seed: str, nonce: int,
                reel_grid_values: list) -> dict:
    """
    Verify that a spin result matches the provably fair hash.

    Args:
        server_seed:      Revealed server seed
        client_seed:      Client seed used for this spin
        nonce:            Nonce used for this spin
        reel_grid_values: 3×5 list of symbol value strings (e.g. 'W', 'D', ...)

    Returns:
        {verified: bool, spin_hash: str, grid_hash: str}
    """
    spin_bytes = generate_spin_bytes(server_seed, client_seed, nonce)
    spin_hash = spin_bytes.hex()

    # Derive what the grid should have been from the hash bytes
    from reel_engine import ReelWeights, _build_cumulative, _pick_from_cumulative
    reels = 5
    rows = 3
    cum_data = [_build_cumulative(ReelWeights.ALL_REELS[r]) for r in range(reels)]
    reel_columns = []
    byte_idx = 0
    for reel_num in range(reels):
        symbols, cumulative, total = cum_data[reel_num]
        col = []
        for _ in range(rows):
            raw = (spin_bytes[byte_idx] << 8) | spin_bytes[byte_idx + 1]
            byte_idx += 2
            col.append(_pick_from_cumulative(raw, symbols, cumulative, total))
        reel_columns.append(col)

    expected_grid = []
    for row in range(rows):
        expected_grid.append([reel_columns[reel][row].value for reel in range(reels)])

    verified = (expected_grid == reel_grid_values)
    return {
        'verified': verified,
        'spin_hash': spin_hash,
        'expected_grid': expected_grid,
        'provided_grid': reel_grid_values,
    }
