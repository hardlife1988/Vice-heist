"""
Vice Heist — Flask backend server.
Serves the game frontend and provides Stake Engine compliant spin API.

Security note:
  All sensitive game state (server_seed, balance, nonce, free-spin status) is
  kept in a SERVER-SIDE in-memory store keyed by a random session_id.
  Only the opaque session_id is stored in the client cookie (signed with
  SESSION_SECRET).  The active server_seed is NEVER sent to the client —
  only sha256(server_seed) is exposed.
"""

import os
import sys
import json
import secrets
import hashlib

# Allow imports from math/ without a package prefix
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "math"))

from flask import Flask, jsonify, request, send_from_directory, session

from game_config import GameConfig
from reel_engine import ReelEngine
from win_evaluator import WinEvaluator
from stake_engine import generate_server_seed, get_server_seed_hash, verify_spin

# ── App setup ────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder="static")

_secret = os.environ.get("SESSION_SECRET")
if not _secret:
    raise RuntimeError(
        "SESSION_SECRET environment variable is not set. "
        "Set it to a random string before starting the server."
    )
app.secret_key = _secret

CONFIG   = GameConfig()
ENGINE   = ReelEngine(CONFIG)
EVALUATOR = WinEvaluator(CONFIG)

# ── Server-side session store ─────────────────────────────────────────────────
# Maps session_id (str) → game state dict.
# In production, replace with Redis / PostgreSQL.
_GAME_SESSIONS: dict[str, dict] = {}


def _new_game_state() -> dict:
    """Create a fresh game state dict (all sensitive fields server-side)."""
    seed, seed_hash = generate_server_seed()
    return {
        "server_seed":          seed,       # NEVER sent to client
        "server_seed_hash":     seed_hash,  # safe to expose
        "client_seed":          "default_client_seed",
        "nonce":                0,
        "balance":              1000.0,
        "free_spins_remaining": 0,
        "in_free_spins":        False,
        "total_wagered":        0.0,
        "total_won":            0.0,
        "spin_history":         [],         # last 20 spin summaries
    }


def _get_game_state() -> dict:
    """Return (or create) the server-side game state for the current request."""
    sid = session.get("sid")
    if sid is None or sid not in _GAME_SESSIONS:
        sid = secrets.token_urlsafe(32)
        _GAME_SESSIONS[sid] = _new_game_state()
        session["sid"] = sid          # opaque ID only — no game data in cookie
        session.permanent = False
    return _GAME_SESSIONS[sid]


def _rotate_server_seed(gs: dict) -> str:
    """Reveal the old server seed and generate a fresh one. Returns old seed."""
    old_seed = gs["server_seed"]
    new_seed, new_hash = generate_server_seed()
    gs["server_seed"]      = new_seed
    gs["server_seed_hash"] = new_hash
    gs["nonce"]            = 0
    return old_seed


# ── Static file serving ───────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


# Allowlist of extensions safe to serve from the static/ directory.
_SAFE_EXTENSIONS = {".html", ".css", ".js", ".png", ".jpg", ".jpeg",
                    ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf"}


@app.route("/<path:filename>")
def static_files(filename):
    # Block dotfiles and anything outside the static/ directory.
    parts = filename.replace("\\", "/").split("/")
    if any(p.startswith(".") or p in ("", "..") for p in parts):
        return "", 403
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _SAFE_EXTENSIONS:
        return "", 403
    return send_from_directory("static", filename)


# ── API: game config ──────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def api_config():
    gs = _get_game_state()
    return jsonify({
        **CONFIG.to_dict(),
        "server_seed_hash":     gs["server_seed_hash"],
        "client_seed":          gs["client_seed"],
        "nonce":                gs["nonce"],
        "balance":              gs["balance"],
        "free_spins_remaining": gs["free_spins_remaining"],
        "in_free_spins":        gs["in_free_spins"],
    })


# ── API: spin ─────────────────────────────────────────────────────────────────

@app.route("/api/spin", methods=["POST"])
def api_spin():
    gs = _get_game_state()
    data = request.get_json(silent=True) or {}

    # --- Safe input parsing ---
    try:
        bet = float(data.get("bet", CONFIG.default_bet))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid bet value"}), 400

    is_bonus_buy = bool(data.get("bonus_buy", False))
    bet = round(max(CONFIG.min_bet, min(CONFIG.max_bet, bet)), 4)

    # --- Determine spin type BEFORE any state changes ---
    # Priority: bonus_buy > free_spin > normal
    if is_bonus_buy:
        cost       = round(bet * CONFIG.bonus_buy_cost, 4)
        multiplier = CONFIG.free_spins_multiplier
        is_free    = False   # this spin itself is paid; FS are granted after
    elif gs["in_free_spins"] and gs["free_spins_remaining"] > 0:
        cost       = 0.0
        multiplier = CONFIG.free_spins_multiplier
        is_free    = True
    else:
        cost       = bet
        multiplier = 1.0
        is_free    = False

    if gs["balance"] < cost:
        return jsonify({"error": "Insufficient balance"}), 400

    # --- Deduct cost ---
    gs["balance"]       = round(gs["balance"] - cost, 4)
    gs["total_wagered"] = round(gs["total_wagered"] + cost, 4)

    # --- For bonus buy: grant free spins BEFORE spinning so multiplier applies ---
    if is_bonus_buy:
        gs["free_spins_remaining"] = CONFIG.free_spins_count
        gs["in_free_spins"]        = True
        # This spin counts as first free spin
        is_free    = True
        cost_label = "bonus_buy"
    else:
        cost_label = "free" if is_free else "normal"

    # --- Provably fair spin ---
    server_seed = gs["server_seed"]
    client_seed = gs["client_seed"]
    nonce       = gs["nonce"]
    gs["nonce"] += 1

    grid = ENGINE.spin_reels(server_seed, client_seed, nonce)

    # --- Evaluate wins ---
    result = EVALUATOR.evaluate_spin(grid, bet, multiplier)

    # Apply max win cap
    total_win = min(result["total_win"], bet * CONFIG.max_win)
    gs["balance"]   = round(gs["balance"] + total_win, 4)
    gs["total_won"] = round(gs["total_won"] + total_win, 4)

    # --- Update free-spin state ---
    if is_free:
        gs["free_spins_remaining"] = max(0, gs["free_spins_remaining"] - 1)
        if gs["free_spins_remaining"] == 0:
            gs["in_free_spins"] = False
    elif result["triggers_free_spins"]:
        gs["free_spins_remaining"] = CONFIG.free_spins_count
        gs["in_free_spins"]        = True

    # --- Serialise grid ---
    grid_values = [[sym.value for sym in row] for row in grid]

    # --- Append to spin history (keep last 20) ---
    spin_record = {
        "nonce":            nonce,
        "client_seed":      client_seed,
        "server_seed_hash": gs["server_seed_hash"],
        "grid":             grid_values,
        "bet":              bet,
        "win":              total_win,
        "multiplier":       multiplier,
        "type":             cost_label,
    }
    gs["spin_history"].insert(0, spin_record)
    gs["spin_history"] = gs["spin_history"][:20]

    return jsonify({
        "reel_grid":            grid_values,
        "win":                  round(total_win, 4),
        "payline_wins":         result["payline_wins"],
        "scatter_count":        result["scatter_count"],
        "scatter_win":          result["scatter_win"],
        "triggers_free_spins":  result["triggers_free_spins"],
        "free_spins_remaining": gs["free_spins_remaining"],
        "in_free_spins":        gs["in_free_spins"],
        "balance":              gs["balance"],
        "nonce":                nonce,
        "server_seed_hash":     gs["server_seed_hash"],
        "client_seed":          client_seed,
        "multiplier":           multiplier,
        "is_free_spin":         is_free,
        "is_bonus_buy":         is_bonus_buy,
    })


# ── API: update client seed ───────────────────────────────────────────────────

@app.route("/api/seed", methods=["POST"])
def api_set_seed():
    gs = _get_game_state()
    data = request.get_json(silent=True) or {}
    new_client_seed = str(data.get("client_seed", "")).strip()
    if not new_client_seed:
        return jsonify({"error": "client_seed cannot be empty"}), 400

    # Reveal old server seed, generate new one, reset nonce
    old_server_seed = _rotate_server_seed(gs)
    gs["client_seed"] = new_client_seed

    return jsonify({
        "ok":                   True,
        "revealed_server_seed": old_server_seed,   # now safe to reveal
        "new_server_seed_hash": gs["server_seed_hash"],
        "client_seed":          new_client_seed,
        "nonce":                0,
    })


# ── API: verify spin ──────────────────────────────────────────────────────────

@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json(silent=True) or {}
    try:
        server_seed = str(data["server_seed"])
        client_seed = str(data["client_seed"])
        nonce       = int(data["nonce"])
        reel_grid   = data["reel_grid"]
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Missing or invalid field: {e}"}), 400

    if not isinstance(reel_grid, list) or len(reel_grid) != 3:
        return jsonify({"error": "reel_grid must be a 3-element array"}), 400

    result = verify_spin(server_seed, client_seed, nonce, reel_grid)
    return jsonify(result)


# ── API: deposit (demo) ───────────────────────────────────────────────────────

@app.route("/api/deposit", methods=["POST"])
def api_deposit():
    gs = _get_game_state()
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 1000.0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400
    amount = min(max(amount, 1), 100_000)
    gs["balance"] = round(gs["balance"] + amount, 4)
    return jsonify({"balance": gs["balance"]})


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
