import os
import sys
import json
from datetime import datetime

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

def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    output_dir = os.path.join(os.path.dirname(__file__), 'library', 'publish_files')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def save_results(output_dir, config, gamestate, configs):
    """Save simulation results to files."""
    timestamp = datetime.now().isoformat()
    
    # Save game configuration
    config_file = os.path.join(output_dir, 'game_config.json')
    with open(config_file, 'w') as f:
        json.dump(config.to_dict(), f, indent=2)
    print(f"✓ Saved: {config_file}")
    
    # Save generated configs
    configs_file = os.path.join(output_dir, 'game_configs.json')
    with open(configs_file, 'w') as f:
        json.dump(configs, f, indent=2)
    print(f"✓ Saved: {configs_file}")
    
    # Save simulation metadata
    metadata = {
        "timestamp": timestamp,
        "game": "Vice-heist",
        "simulations": {
            "base_game": num_sim_args["base"],
            "bonus_feature": num_sim_args["bonus"],
        },
        "settings": {
            "num_threads": num_threads,
            "batching_size": batching_size,
            "compression": compression,
            "profiling": profiling,
        },
        "game_state": {
            "total_spins": gamestate.total_spins,
            "total_wagered": gamestate.total_wagered,
            "total_won": gamestate.total_won,
            "final_balance": gamestate.current_balance,
        }
    }
    
    metadata_file = os.path.join(output_dir, 'simulation_metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Saved: {metadata_file}")
    
    # Save simulation results summary
    results = {
        "game": "Vice-heist",
        "max_win": config.max_win,
        "rtp": config.rtp,
        "volatility": config.volatility,
        "features": {
            "free_spins": {
                "trigger": config.free_spins_trigger,
                "count": config.free_spins_count,
            },
            "bonus_vault": config.bonus_vault_available,
        },
        "simulation_results": metadata["game_state"],
    }
    
    results_file = os.path.join(output_dir, 'simulation_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"✓ Saved: {results_file}")

def main():
    print("\n" + "="*50)
    print("Vice-heist Math Simulation")
    print("="*50 + "\n")
    
    # Initialize game
    config = GameConfig()
    gamestate = GameState(config)
    
    print(f"Game: {config.name}")
    print(f"Reels: {config.reels}x{config.rows}")
    print(f"RTP: {config.rtp*100}%")
    print(f"Max Win: {config.max_win}x")
    print(f"Volatility: {config.volatility}\n")
    
    # Run simulation
    print("Running simulations...")
    create_books(
        gamestate=gamestate,
        config=config,
        num_sim_args=num_sim_args,
        batching_size=batching_size,
        num_threads=num_threads,
        compression=compression,
        profiling=profiling,
    )
    configs = generate_configs(gamestate)
    
    # Ensure output directory exists
    output_dir = ensure_output_dir()
    print(f"\nOutput directory: {output_dir}")
    
    # Save results
    print("\nSaving results...")
    save_results(output_dir, config, gamestate, configs)
    
    print("\n" + "="*50)
    print("✓ Vice Heist simulation complete!")
    print(f"✓ Output files saved to: {output_dir}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
