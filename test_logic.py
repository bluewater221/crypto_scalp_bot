import unittest
from trade_manager import TradeManager
import os
import json

class TestTradeManager(unittest.TestCase):
    def setUp(self):
        self.trades_file = 'test_trades.json'
        self.history_file = 'test_history.json'
        # Clean up files if they exist
        for f in [self.trades_file, self.history_file]:
            if os.path.exists(f):
                os.remove(f)
        
        self.tm = TradeManager(
            market_tag='TEST_CRYPTO',
            trades_file=self.trades_file,
            history_file=self.history_file,
            initial_capital=100
        )

    def tearDown(self):
        # Clean up files
        for f in [self.trades_file, self.history_file]:
            if os.path.exists(f):
                os.remove(f)

    def test_initial_balance(self):
        self.assertEqual(self.tm.calculate_balance(), 100)

    def test_add_trade_and_calculate_balance(self):
        # Simulate a winning trade
        # Risk 1% of 100 = 1.0
        # Entry 100, SL 99 (1% distance)
        # Position Size = 1.0 / 0.01 = 100
        # Exit 101 (1% profit)
        # PnL = (101 - 100) * (100 / 100) = 1.0
        trade = {
            'symbol': 'BTC/USDT',
            'side': 'LONG',
            'entry': 100,
            'sl': 99,
            'close_price': 101,
            'outcome': 'WIN',
            'risk_pct': 0.01
        }
        self.tm.history.append(trade)
        balance = self.tm.calculate_balance()
        self.assertAlmostEqual(balance, 101.0)

    def test_compounding_balance(self):
        # Trade 1: Win 1% -> 101
        self.tm.history.append({
            'symbol': 'BTC/USDT', 'side': 'LONG', 'entry': 100, 'sl': 99, 'close_price': 101, 'outcome': 'WIN', 'risk_pct': 0.01
        })
        # Trade 2: Loss 1% of 101 -> 1.01 risk. SL at 1% distance.
        # Position size = 1.01 / 0.01 = 101
        # Entry 100, SL 99, Exit 99
        # PnL = (99 - 100) * (101 / 100) = -1.01
        # Balance = 101 - 1.01 = 99.99
        self.tm.history.append({
            'symbol': 'BTC/USDT', 'side': 'LONG', 'entry': 100, 'sl': 99, 'close_price': 99, 'outcome': 'LOSS', 'risk_pct': 0.01
        })
        balance = self.tm.calculate_balance()
        self.assertAlmostEqual(balance, 99.99)

if __name__ == '__main__':
    unittest.main()
