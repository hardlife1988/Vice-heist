"""
Win Evaluator for Vice-heist slot game.
Evaluates payline wins and calculates winnings.
"""

from paytable import Paytable, Symbol


class WinEvaluator:
    """Evaluates wins from reel combinations."""
    
    def __init__(self, config):
        self.config = config
        self.paytable = Paytable()
    
    def evaluate_spin(self, reel_grid, bet_amount, multiplier=1.0):
        """
        Evaluate all paylines for wins.
        
        Args:
            reel_grid: 3x5 grid of symbols from spin
            bet_amount: Bet amount per line
            multiplier: Feature multiplier (e.g., free spins)
            
        Returns:
            dict: Win information
                {
                    'total_win': float,
                    'wins': [list of individual payline wins],
                    'scatter_count': int,
                    'triggers_free_spins': bool,
                }
        """
        total_win = 0
        wins = []
        scatter_count = 0
        triggers_free_spins = False
        
        # Check each payline
        for payline_num in range(1, self.config.paylines + 1):
            payline = Paytable.get_payline(payline_num)
            payline_win = self._evaluate_payline(reel_grid, payline, bet_amount, multiplier)
            
            if payline_win > 0:
                total_win += payline_win
                wins.append({
                    'payline': payline_num,
                    'win': payline_win,
                })
        
        # Check for scatter (free spins trigger)
        scatter_positions = self._find_scatters(reel_grid)
        scatter_count = len(scatter_positions)
        
        if scatter_count >= self.config.free_spins_trigger:
            triggers_free_spins = True
            # Scatters pay independently
            scatter_win = scatter_count * bet_amount * 5  # 5x per scatter
            total_win += scatter_win
        
        return {
            'total_win': total_win,
            'wins': wins,
            'scatter_count': scatter_count,
            'triggers_free_spins': triggers_free_spins,
        }
    
    def _evaluate_payline(self, reel_grid, payline, bet_amount, multiplier):
        """
        Evaluate a single payline.
        
        Args:
            reel_grid: 3x5 grid of symbols
            payline: List of row positions for each reel
            bet_amount: Bet per line
            multiplier: Feature multiplier
            
        Returns:
            float: Win amount for this payline
        """
        # Extract symbols on this payline
        payline_symbols = []
        for reel, row in enumerate(payline):
            payline_symbols.append(reel_grid[row][reel])
        
        # Check for matches from left to right
        win = 0
        
        # Check for consecutive matches from reel 0
        first_symbol = payline_symbols[0]
        
        # Handle wilds - wilds match any symbol
        consecutive_count = 1
        for i in range(1, len(payline_symbols)):
            current = payline_symbols[i]
            
            # Wild matches anything or if same symbol
            if (current == Symbol.WILD or first_symbol == Symbol.WILD or current == first_symbol):
                consecutive_count += 1
            else:
                break
        
        # Determine which symbol won (prefer non-wild)
        winning_symbol = first_symbol
        if first_symbol == Symbol.WILD and consecutive_count > 1:
            # Find the non-wild symbol if available
            for sym in payline_symbols[1:consecutive_count]:
                if sym != Symbol.WILD:
                    winning_symbol = sym
                    break
        
        # Calculate win (minimum 3 consecutive matches)
        if consecutive_count >= 3 and winning_symbol != Symbol.SCATTER:
            win = Paytable.calculate_win(
                winning_symbol,
                consecutive_count,
                bet_amount,
                multiplier
            )
        
        return win
    
    def _find_scatters(self, reel_grid):
        """
        Find all scatter (Book) symbols on reels.
        
        Args:
            reel_grid: 3x5 grid of symbols
            
        Returns:
            list: Positions of scatter symbols [(row, reel), ...]
        """
        scatters = []
        for row in range(len(reel_grid)):
            for reel in range(len(reel_grid[row])):
                if reel_grid[row][reel] == Symbol.SCATTER:
                    scatters.append((row, reel))
        return scatters
