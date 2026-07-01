
---

### 2. `math/game_config.py`

```python
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from config import Config
from betmode import BetMode, Distribution

class GameConfig(Config):
    def __init__(self):
        super().__init__()
        self.game_id = "vice_heist"
        self.provider_number = 0
        self.working_name = "Vice Heist"
        self.wincap = 10000
        self.win_type = "lines"
        self.rtp = 96.0
        self.num_reels = 5
        self.num_rows = [3, 3, 3, 3, 3]
        
        self.paytable = {
            (5, "diamond"): 1000, (4, "diamond"): 200, (3, "diamond"): 50,
            (5, "gold_bar"): 750, (4, "gold_bar"): 150, (3, "gold_bar"): 40,
            (5, "cash_stack"): 500, (4, "cash_stack"): 100, (3, "cash_stack"): 30,
            (5, "heist_bag"): 400, (4, "heist_bag"): 80, (3, "heist_bag"): 25,
            (5, "vault"): 300, (4, "vault"): 60, (3, "vault"): 20,
            (5, "A"): 150, (4, "A"): 40, (3, "A"): 10,
            (5, "K"): 120, (4, "K"): 30, (3, "K"): 8,
            (5, "Q"): 100, (4, "Q"): 25, (3, "Q"): 6,
            (5, "J"): 80, (4, "J"): 20, (3, "J"): 4,
        }
        
        self.special_symbols = {
            "wild": ["wild"],
            "scatter": ["scatter"],
            "bonus": ["bonus_vault"],
        }
        
        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv"}
        self.reels = {}
        self.reels_path = os.path.join(os.path.dirname(__file__), "reels")
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(str.join("/", [self.reels_path, f]))
        
        self.freespin_triggers = {
            self.basegame_type: {3: 10, 4: 15, 5: 20},
            self.freegame_type: {2: 4, 3: 6, 4: 8, 5: 10},
        }
        
        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "mult_values": {
                                self.basegame_type: {1: 1},
                                self.freegame_type: {2: 10, 3: 20, 4: 50, 5: 60, 10: 100, 20: 90, 50: 50},
                            },
                            "scatter_triggers": {4: 1, 5: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.05,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {3: 20, 4: 10, 5: 2},
                            "mult_values": {
                                self.basegame_type: {1: 1},
                                self.freegame_type": {2: 100, 3: 80, 4: 50, 5: 20, 10: 10, 20: 5, 50: 1},
                            },
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.449,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.5,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                        },
                    ),
                ],
            ),
            BetMode(
                name="bonus",
                cost=100.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "mult_values": {
                                self.freegame_type: {2: 10, 3: 20, 4: 50, 5: 60, 10: 100, 20: 90, 50: 50},
                            },
                            "scatter_triggers": {4: 1, 5: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
                        conditions={
                            "reel_weights": {
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {3: 20, 4: 10, 5: 2},
                            "mult_values": {
                                self.freegame_type: {2: 100, 3: 80, 4: 50, 5: 20, 10: 10, 20: 5, 50: 1},
                            },
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                ],
            ),
        ]
        
        self.winlines = [
            [0,0,0,0,0], [1,1,1,1,1], [2,2,2,2,2],
            [0,1,2,1,0], [2,1,0,1,2], [0,0,1,0,0],
            [2,2,1,2,2], [1,2,2,2,1], [1,0,0,0,1],
            [0,1,1,1,0], [2,1,1,1,2], [1,2,1,2,1],
            [1,0,1,0,1], [0,2,0,2,0], [2,0,2,0,2],
            [0,1,0,1,0], [2,1,2,1,2], [1,1,0,1,1],
            [1,1,2,1,1], [0,0,2,0,0],
        ]
        
        self.include_padding = True
