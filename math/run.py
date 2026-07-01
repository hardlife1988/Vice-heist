import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from books import create_books
from configs import generate_configs
from game_config import GameConfig
from gamestate import GameState

num_threads = 4
batching_size = 10000
compression = True
profiling = False

num_sim_args = {
    "base": 1000000,
    "bonus": 100000,
}

def main():
    config = GameConfig()
    gamestate = GameState(config)
    create_books(
        gamestate=gamestate,
        config=config,
        num_sim_args=num_sim_args,
        batching_size=batching_size,
        num_threads=num_threads,
        compression=compression,
        profiling=profiling,
    )
    generate_configs(gamestate)
    print("\nVice Heist (10,000x) complete!")
    print("Output: math/library/publish_files/")

if __name__ == "__main__":
    main()
