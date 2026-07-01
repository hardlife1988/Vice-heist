import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from gamestate import GameState as BaseGameState
from executables import Executables

class GameState(BaseGameState):
    def __init__(self, config):
        super().__init__(config)
        self.executables = Executables(self.config)
    
    def run_spin(self):
        self.reset_seed(self.sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()
            line_wins = self.executables.evaluate_line_wins(self.board, self.config.winlines)
            total_payout = sum(win["payout"] for win in line_wins)
            scatter_count = self.count_scatters(self.board)
            free_spins_awarded = 0
            if scatter_count >= 3 and self.gametype == self.config.basegame_type:
                free_spins_awarded = self.config.freespin_triggers[self.config.basegame_type].get(scatter_count, 0)
            events = []
            events.append({"type": "reveal", "board": self.board})
            for win in line_wins:
                events.append({"type": "winInfo", "line": win["line_index"], "symbol": win["symbol"], "count": win["count"], "positions": win["positions"], "winAmount": win["payout"]})
            if free_spins_awarded > 0:
                events.append({"type": "scatterTrigger", "count": scatter_count, "freeSpins": free_spins_awarded})
            self.wallet_manager.update(total_payout)
            self.win_manager.update_gametype_wins(self.gametype)
            if self.check_fs_condition():
                self.run_freespin_from_base()
            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()
        return {"id": self.sim_id, "events": events, "payoutMultiplier": self.payout_multiplier}
    
    def run_freespin(self):
        self.update_freespin()
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()
            line_wins = self.executables.evaluate_line_wins(self.board, self.config.winlines)
            total_payout = sum(win["payout"] for win in line_wins)
            scatter_count = self.count_scatters(self.board)
            retrigger_spins = 0
            if self.gametype == self.config.freegame_type:
                retrigger_spins = self.config.freespin_triggers[self.config.freegame_type].get(scatter_count, 0)
            events = []
            events.append({"type": "reveal", "board": self.board})
            for win in line_wins:
                events.append({"type": "winInfo", "line": win["line_index"], "symbol": win["symbol"], "count": win["count"], "positions": win["positions"], "winAmount": win["payout"]})
            if retrigger_spins > 0:
                events.append({"type": "retrigger", "count": scatter_count, "freeSpins": retrigger_spins})
            self.wallet_manager.update(total_payout)
            self.win_manager.update_gametype_wins(self.gametype)
            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()
        return {"id": self.sim_id, "events": events, "payoutMultiplier": self.payout_multiplier}
    
    def count_scatters(self, board):
        count = 0
        for reel in board:
            for symbol in reel:
                if symbol == "scatter":
                    count += 1
        return count
