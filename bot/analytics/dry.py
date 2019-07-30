from abc import ABCMeta, abstractmethod
from analytics.base import AbstractAnalytics

import datetime
from tabulate import tabulate

import redis
from helpers import load_config


class DryAnalytics(AbstractAnalytics):
    def __init__(self):
        self.redis = redis.Redis(decode_responses=True)
        self.config = load_config()
        self.symbol_list = self.config['symbol_list']

        self.trades = {
            symbol: {
                'is_open': False,
                'open_since': None,
                'open_date': None,
                'open_price': 0.0,
                'current_value': 0.0,
                'current_profit': 0.0
            }
            for symbol in self.symbol_list
        }

    def balance(self):
        """
        Calculate account balance per currency
        """
        total = self.redis.get('total')
        cash = self.redis.get('cash')
        pending = float(total) - float(cash)

        return {
            'total': total,
            'cash': cash,
            'pending': pending
        }

    def print_balance(self):
        balance = self.balance()
        columns = ['Available', 'Total', 'Pending']

        print(tabulate([[balance["cash"], balance["total"],
                         balance["pending"]]], headers=columns))

    def status(self):
        """
        Lists all open trades
        """
        open_trades = []

        for symbol in self.symbol_list:
            is_open = int(self.redis.hget(f'symbol:{symbol}', 'is_open'))
            if is_open:
                self.open_trades['is_open'] = is_open
                self.open_trades['open_since'] = self.redis.hget(
                    f'symbol:{symbol}', 'open_date')
                self.open_trades['open_price'] = self.redis.hget(
                    f'symbol:{symbol}', 'open_price')
                self.open_trades['current_value'] = self.redis.hget(
                    f'symbol:{symbol}', 'current_value')
                self.open_trades['current_profit'] = (
                    (current_value / open_price) - 1) * 100

    def print_status(self):
        columns = ['Current Symbol', 'Open Since',
                   'Open Price', 'Current Value', 'Current Profit (%)']
        table = []
        for trade in self.trades:
            if trade.is_open:
                row = [
                    trade['symbol'],
                    trade['open_date'],
                    trade['open_price'],
                    trade['current_value'],
                    trade['current_profit']
                ]
                table.append(row)

        print(tabulate(table, headers=columns))

    def profit(self):
        """
        Display a summary of profit/loss from close trades and some stats of performance
        """
        pass

    def print_profit(self):
        pass

    def performance(self):
        """
        Show performance of each finished trade grouped by symbol
        """
        pass

    def print_performance(self):
        pass

    def daily(self, n):
        """
        Shows profit or loss per day, over the last n days
        """
        pass

    def print_daily(self):
        pass
