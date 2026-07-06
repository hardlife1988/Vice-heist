import json
import os

# Game Config for Stake
config = {
    "name": "Vice Heist",
    "reels": 5,
    "rows": 3,
    "rtp": 96.0,
    "max_win": 10000,
    "features": ["free_spins", "bonus_vault"]
}

# Create output for Stake
os.makedirs("publish_files", exist_ok=True)

with open("publish_files/game_config.json", "w") as f:
    json.dump(config, f, indent=2)

print("✅ Stake-ready files generated!")
print("Upload the 'publish_files' folder to Stake.")
