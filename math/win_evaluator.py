"""
Win Evaluator for Vice-heist slot game.
Evaluates 20-payline wins, scatter wins, and free spin triggers.
"""

from paytable import Paytable, Symbol


class WinEvaluator:
    """Evaluates wins from a 3×5 reel grid."""

    def __init__(self, config):
        self.config = config

    def evaluate_spin(self, reel_grid: list, total_bet: float, multiplier: float = 1.0) -> dict:
        """
        Evaluate all paylines and scatters for a single spin.

        Args:
            reel_grid:  list[3][5] of Symbol — grid[row][reel]
            total_bet:  Total amount wagered (all lines)
            multiplier: Feature multiplier (e.g. 2.0 during free spins)

        Returns:
            {
                'total_win': float,
                'payline_wins': [{'payline': int, 'symbol': str, 'count': int, 'win': float}],
                'scatter_count': int,
                'triggers_free_spins': bool,
                'scatter_win': float,
            }
        """
        total_win = 0.0
        payline_wins = []

        for line_num in range(1, self.config.paylines + 1):
            payline = Paytable.get_payline(line_num)
            if not payline:
                continue
            result = self._evaluate_payline(reel_grid, payline, total_bet, multiplier)
            if result and result['win'] > 0:
                result['payline'] = line_num
                total_win += result['win']
                payline_wins.append(result)

        # Scatter pays anywhere — independent of paylines
        scatter_count = self._count_scatters(reel_grid)
        scatter_win = 0.0
        triggers_free_spins = False

        if scatter_count >= self.config.free_spins_trigger:
            triggers_free_spins = True
            # Scatter pay: 2× / 5× / 10× total bet for 3 / 4 / 5 scatters
            scatter_pay = {3: 2, 4: 5, 5: 10}.get(min(scatter_count, 5), 2)
            scatter_win = scatter_pay * total_bet * multiplier
            total_win += scatter_win

        return {
            'total_win': round(total_win, 4),
            'payline_wins': payline_wins,
            'scatter_count': scatter_count,
            'triggers_free_spins': triggers_free_spins,
            'scatter_win': round(scatter_win, 4),
        }

    def _evaluate_payline(self, reel_grid: list, payline: list, total_bet: float, multiplier: float) -> dict | None:
        """Evaluate a single payline and return win info or None."""
        # Extract the symbol on each reel for this payline
        line_symbols = [reel_grid[payline[reel]][reel] for reel in range(len(payline))]

        # Determine the leading (non-wild) symbol
        lead = None
        for sym in line_symbols:
            if sym not in (Symbol.WILD, Symbol.SCATTER):
                lead = sym
                break

        # Count consecutive matching symbols from reel 0
        count = 0
        for sym in line_symbols:
            if sym == Symbol.WILD or sym == lead:
                count += 1
            elif lead is None and sym != Symbol.SCATTER:
                # All wilds so far — keep going but track lead
                lead = sym
                count += 1
            else:
                break

        # Wilds-only line: treat as Wild symbol win
        if lead is None and count > 0:
            lead = Symbol.WILD

        if count < 3 or lead is None or lead == Symbol.SCATTER:
            return None

        win = Paytable.calculate_win(lead, count, total_bet, multiplier)
        if win <= 0:
            return None

        return {
            'symbol': Paytable.get_symbol_name(lead),
            'symbol_key': lead.value,
            'count': count,
            'win': win,
        }

    def _count_scatters(self, reel_grid: list) -> int:
        count = 0
        for row in reel_grid:
            for sym in row:
                if sym == Symbol.SCATTER:
                    count += 1
        return count
