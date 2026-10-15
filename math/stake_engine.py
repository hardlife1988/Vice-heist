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
                reel_grid_values: list, mode: str = "base") -> dict:
    """Verify local engine results using the engine's current RNG and reel mode.

    This local diagnostic is independent of Stake RGS book selection.
    """
    from reel_engine import spin_provably_fair
    expected = [[symbol.value for symbol in row] for row in
                spin_provably_fair(server_seed, client_seed, nonce, mode=mode)]
    return {"verified": expected == reel_grid_values,
            "expected_grid": expected, "provided_grid": reel_grid_values,
            "mode": mode}
