import os
import sys
import json
from datetime import datetime

# Add math folder to path
sys.path.insert(0, os.path.dirname(__file__))

from game_config import GameConfig
from gamestate import GameState
# from books import create_books  # Comment out if broken

def main():
    print("Starting Vice Heist Math...")
    config = GameConfig()
    gamestate = GameState(config)
    
    print(f"Game: {config.name}")
    print(f"RTP Target: {config.rtp*100}%")
    
    # Simple test spin
    print("Test spin ready. Full simulation needs fixes.")
    
    # Save basic config
    os.makedirs("library/publish_files", exist_ok=True)
    with open("library/publish_files/game_config.json", "w") as f:
        json.dump(config.to_dict(), f, indent=2)
    
    print("✅ Basic files created!")

if __name__ == "__main__":
    main()
