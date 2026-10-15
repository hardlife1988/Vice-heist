"""Evaluate Vice Heist paylines, scatters, and free-spin triggers."""

from paytable import Paytable, Symbol


class WinEvaluator:
    """Evaluates wins from a three-row, five-reel grid."""

    def __init__(self, config):
        self.config = config

    def evaluate_spin(
        self,
        reel_grid: list,
        total_bet: float,
        multiplier: float = 1.0,
    ) -> dict:
        """Evaluate all paylines and scatter wins for one spin."""
        if (
            len(reel_grid) != 3
            or any(len(row) != 5 for row in reel_grid)
        ):
            raise ValueError("Reel grid must have 3 rows and 5 reels")

        if total_bet <= 0 or multiplier <= 0:
            raise ValueError("Bet and multiplier must be positive")

        total_win = 0.0
        payline_wins = []

        for line_num in range(1, self.config.paylines + 1):
            payline = Paytable.get_payline(line_num)
            if not payline:
                continue

            result = self._evaluate_payline(
                reel_grid, payline, total_bet, multiplier
            )

            if result is not None and result["win"] > 0:
                result["payline"] = line_num
                total_win += result["win"]
                payline_wins.append(result)

        scatter_count = self._count_scatters(reel_grid)
        triggers_free_spins = (
            scatter_count >= self.config.free_spins_trigger
        )

        scatter_win = 0.0
        if triggers_free_spins:
            scatter_multiplier = {
                3: 2,
                4: 5,
                5: 10,
            }.get(min(scatter_count, 5), 0)

            scatter_win = round(
                scatter_multiplier * total_bet * multiplier, 4
            )
            total_win += scatter_win

        return {
            "total_win": round(total_win, 4),
            "payline_wins": payline_wins,
            "scatter_count": scatter_count,
            "triggers_free_spins": triggers_free_spins,
            "scatter_win": scatter_win,
        }

    def _evaluate_payline(
        self,
        reel_grid: list,
        payline: list,
        total_bet: float,
        multiplier: float,
    ) -> dict | None:
        """Choose the highest-paying valid Wild substitution."""
        if len(payline) != 5 or any(
            not isinstance(row, int) or row not in (0, 1, 2)
            for row in payline
        ):
            raise ValueError("Payline must contain five row indices")

        line_symbols = [
            reel_grid[payline[reel]][reel]
            for reel in range(5)
        ]

        best_result = None

        # A Wild can represent itself or any regular paying symbol.
        # Evaluate each interpretation and retain the highest payout.
        for target in Symbol:
            if target == Symbol.SCATTER:
                continue

            count = 0
            for symbol in line_symbols:
                if symbol == target or symbol == Symbol.WILD:
                    count += 1
                else:
                    break

            if count < 3:
                continue

            win = Paytable.calculate_win(
                target, count, total_bet, multiplier
            )
            if win <= 0:
                continue

            if best_result is None or win > best_result["win"]:
                best_result = {
                    "symbol": Paytable.get_symbol_name(target),
                    "symbol_key": target.value,
                    "count": count,
                    "win": win,
                }

        return best_result

    @staticmethod
    def _count_scatters(reel_grid: list) -> int:
        return sum(
            symbol == Symbol.SCATTER
            for row in reel_grid
            for symbol in row
        )
