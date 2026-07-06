"""
GameConfig class for Vice-heist slot game.
"""


class GameConfig:
    def __init__(self):
        self.name             = "Vice Heist"
        self.reels            = 5
        self.rows             = 3
        self.paylines         = 20
        self.min_bet          = 0.20   # total bet (all lines)
        self.max_bet          = 100.00
        self.default_bet      = 1.00
        self.rtp              = 0.96
        self.volatility       = "HIGH"
        self.max_win          = 10000  # x total bet
        self.free_spins_trigger = 3   # 3+ scatters anywhere
        self.free_spins_count   = 10
        self.free_spins_multiplier = 2.0
        self.bonus_vault_available = True
        self.bonus_buy_cost   = 100   # x total bet

    def to_dict(self):
        return self.__dict__
