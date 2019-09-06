import queue

from math import floor
import numpy as np
import pandas as pd
from performance import create_sharpe_ratio, create_drawdowns

from event import OrderEvent, FillEvent
from trade import Trade
from helpers import load_config

from pathlib import Path
import redis


class Portfolio:
    """
    The Portfolio class handles the positions and market value of all instruments at a resolution of a "bar", i.e. secondly, minutely, 5-min, 30-min, 60 min.
    The positions dict stores a time-index of the quantity of positions held.
    The holdings dict stores the cash and total market holdings value of each symbol for a particular time-index, as well as the percentage change in portfolio total across bars.
    """

    def __init__(self, events, data_handler, start_date, initial_capital):
        self.config = load_config()
        self.events = events

        self.data_handler = data_handler
        self.symbol_list = self.data_handler.symbol_list

        self.start_date = start_date
        self.initial_capital = initial_capital

        # Current positions and holdings are init to 0
        self.current_positions = self._construct_current_positions()
        self.all_positions = self._construct_all_positions()

        self.current_holdings = self._construct_current_holdings()
        self.all_holdings = self._construct_all_holdings()

        # Money Management
        self.pct_capital_risk = 0.5

        self.trades = None

        self.redis = redis.Redis()

        self.indicators = dict()

    def __repr__(self):
        return f'<Portfolio: Initial capital {self.initial_capital}>'

    def __str__(self):
        return f'Portfolio starting at {self.start_date} with {self.initial_capital} of initial capital.'

    def _construct_current_positions(self):
        """
        This constructs the dictionary which will hold the instantaneous position quantity of the portfolio across all symbols.
        """
        positions = dict((s, 0.0) for s in self.symbol_list)

        return positions

    def _construct_all_positions(self):
        """
        Constructs the positions list using the start_date to determine when the time index will begin.
        """
        positions = self._construct_current_positions()
        positions['datetime'] = self.start_date

        return [positions]

    def _construct_current_holdings(self):
        """
        This constructs the dictionary which will hold the instantaneous value of the portfolio across all symbols.
        """
        holdings = {
            s: {
                'open_date': None,
                'open_price': 0.0,
                'current_value': 0.0,
                'is_open': False,
                'exposition': 0.0,
                'direction': 'OUT'
            }
            for s in self.symbol_list
        }

        holdings['cash'] = holdings['total'] = self.initial_capital
        holdings['fees'] = 0.0

        return holdings

    def _construct_all_holdings(self):
        """
        Constructs the holdings list using the start_date to determine when the time index will begin.
        """
        holdings = self._construct_current_holdings()
        holdings['datetime'] = self.start_date

        return [holdings]

    def _update_all_positions(self, datetime):
        """
        It Updates portfolio with the latest positions of all symbols
        It updates in each market data event
        New positions are opened when an order get filled
        """
        latest_positions = {
            **self.current_positions,
            'datetime': datetime
        }
        self.all_positions.append(latest_positions)

    def _update_all_holdings(self, datetime):
        """
        It updates portfolio with the latest market values (current holding value and current trailing SL)
        It updates portfolio money balance: cash, total (cash + open positions), fees

        Current holding value and trailing SL are either updated when an order get filled or when the market moves
        Money balance is updated when an order get filled
        """

        holdings = {
            symbol: {
                'open_date': None,
                'open_price': 0.0,
                'current_value': 0.0,
                'is_open': False,
                'exposition': 0.0,
                'direction': 'OUT'
            }
            for symbol in self.symbol_list
        }
        holdings['datetime'] = datetime
        holdings['cash'] = holdings['total'] = self.current_holdings['cash']
        holdings['fees'] = self.current_holdings['fees']

        for symbol in self.symbol_list:
            current_position = self.current_positions[symbol]
            current_price = self.data_handler.current_price(symbol)
            market_value = current_position * current_price

            holdings[symbol]['current_value'] = market_value
            holdings[symbol]['exposition'] = self.current_holdings[symbol]['exposition']
            holdings[symbol]['open_price'] = self.current_holdings[symbol]['open_price']
            holdings[symbol]['open_date'] = self.current_holdings[symbol]['open_date']
            holdings[symbol]['direction'] = self.current_holdings[symbol]['direction']
            holdings[symbol]['is_open'] = self.current_holdings[symbol]['is_open']

            if holdings[symbol]['direction'] == 'SHORT':
                holdings['total'] += (holdings[symbol]
                                      ['exposition'] - market_value)
            else:
                holdings['total'] += market_value

        self.all_holdings.append(holdings)

        if self.config['run_mode'] != 'backtest':
            with self.redis.pipeline() as pipe:
                pipe.mset({
                    "cash": holdings['cash'],
                    "total": holdings['total']
                })

                for symbol in self.symbol_list:
                    is_open = holdings[symbol]['is_open']
                    pipe.hmset(f'symbol:{symbol}', {
                        'is_open': int(holdings[symbol]['is_open']),
                        'open_price': holdings[symbol]['open_price'],
                        'open_date': holdings[symbol]['open_date'].isoformat() if is_open else '0',
                        'current_value': holdings[symbol]['current_value']
                    })
                pipe.execute()

    def update_all_positions_holdings(self):
        """
        Adds a new record to the positions matrix for the current market data bar.
        This reflects the PREVIOUS bar, i.e. all current market data at this stage is known (OHLCV).
        Makes use of a MarketEvent from the events queue.
        """
        datetime = self.data_handler.get_latest_bar_datetime(
            self.symbol_list[0])

        self._update_all_positions(datetime)
        self._update_all_holdings(datetime)

    def _generate_order(self, signal):
        """
        Based on the signal generated by the strategy, it creates an Order Event object with risk management and position sizing considerations.
        """
        order = None

        symbol = signal.symbol
        direction = signal.signal_type
        strength = signal.strength
        self.indicators = signal.indicators

        order_type = 'MKT'

        current_quantity = self.current_positions[symbol]
        fill_cost = self.data_handler.current_price(symbol)

        # Define the position sizing of the order.
        # TODO: kelly criterion
        position_size = self.current_holdings['cash'] * \
            self.pct_capital_risk * strength

        if direction == 'LONG' and current_quantity == 0:
            order_quantity = position_size / fill_cost
            order = OrderEvent(symbol, order_type,
                               order_quantity, fill_cost, 'BUY')

        if direction == 'EXIT' and current_quantity > 0:
            order_quantity = current_quantity
            order = OrderEvent(symbol, order_type,
                               order_quantity, fill_cost, 'SELL')

        if direction == 'SHORT' and current_quantity == 0:
            order_quantity = position_size / fill_cost
            order = OrderEvent(symbol, order_type,
                               order_quantity, fill_cost, 'SHORTSELL')

        if direction == 'EXITSHORT' and current_quantity > 0:
            order_quantity = current_quantity
            order = OrderEvent(symbol, order_type,
                               order_quantity, fill_cost, 'SHORTCOVER')

        return order

    def send_order(self, event):
        if event.type == 'SIGNAL':
            order_event = self._generate_order(event)

            # Trigger Order event to be sent to the Execution Handler
            self.events.put(order_event)

    def _update_positions_from_fill(self, fill):
        """
        Takes a Fill object and updates the position matrix to
        reflect the new position.

        Parameters:
          fill: The Fill object to update the positions with.
        """
        fill_dir = 0
        if fill.direction == 'BUY' or fill.direction == 'SHORTSELL':
            fill_dir = 1
        elif fill.direction == 'SELL' or fill.direction == 'SHORTCOVER':
            fill_dir = -1

        self.current_positions[fill.symbol] += fill_dir*fill.quantity

    def _update_holdings_from_fill(self, fill):
        """
        Takes a Fill object and updates the holdings matrix to reflect the holdings value.

        Parameters:
          fill: The Fill object to update the holdings with.
        """
        cost = fill.fill_cost * fill.quantity

        if fill.direction == 'BUY':
            self.current_holdings[fill.symbol]['current_value'] += cost
            self.current_holdings[fill.symbol]['open_date'] = self.data_handler.get_latest_bar_value(
                fill.symbol, 'datetime')
            self.current_holdings[fill.symbol]['open_price'] = cost
            self.current_holdings[fill.symbol]['is_open'] = True
            self.current_holdings[fill.symbol]['direction'] = 'LONG'
            self.current_holdings['cash'] -= (cost + fill.fees)
            self.current_holdings['total'] -= (cost + fill.fees)

            Trade(
                fill.symbol,
                'LONG',
                fill.fill_cost,
                self.current_holdings[fill.symbol]['open_date'],
                cost,
                fill.fees,
                self.indicators
            )

        elif fill.direction == 'SELL':
            self.current_holdings[fill.symbol]['current_value'] -= cost
            self.current_holdings[fill.symbol]['is_open'] = False
            self.current_holdings['cash'] += (cost - fill.fees)
            self.current_holdings['total'] += (cost - fill.fees)

            Trade.close(
                self.current_holdings[fill.symbol]['open_date'],
                fill.fill_cost,
                self.data_handler.get_latest_bar_value(
                    fill.symbol, 'datetime'),
                cost,
                fill.fees
            )

        elif fill.direction == 'SHORTSELL':
            self.current_holdings[fill.symbol]['current_value'] += cost
            self.current_holdings[fill.symbol]['open_date'] = self.data_handler.get_latest_bar_value(
                fill.symbol, 'datetime')
            self.current_holdings[fill.symbol]['open_price'] = cost
            self.current_holdings[fill.symbol]['is_open'] = True
            self.current_holdings['cash'] -= fill.fees
            self.current_holdings['total'] -= fill.fees
            self.current_holdings[fill.symbol]['exposition'] = self.current_holdings[fill.symbol]['open_price']
            self.current_holdings[fill.symbol]['direction'] = 'SHORT'

            Trade(
                fill.symbol,
                'SHORT',
                fill.fill_cost,
                self.current_holdings[fill.symbol]['open_date'],
                cost,
                fill.fees
            )

        elif fill.direction == 'SHORTCOVER':
            self.current_holdings[fill.symbol]['current_value'] -= cost
            self.current_holdings[fill.symbol]['is_open'] = False
            self.current_holdings['cash'] += (
                self.current_holdings[fill.symbol]['exposition'] - cost) - fill.fees
            self.current_holdings['total'] += (
                self.current_holdings[fill.symbol]['exposition'] - cost) - fill.fees
            self.current_holdings[fill.symbol]['open_price'] = 0
            self.current_holdings[fill.symbol]['exposition'] = 0
            self.current_holdings[fill.symbol]['direction'] = 'OUT'

            Trade.close(
                self.current_holdings[fill.symbol]['open_date'],
                fill.fill_cost,
                self.data_handler.get_latest_bar_value(
                    fill.symbol, 'datetime'),
                cost,
                fill.fees
            )

        self.current_holdings['fees'] += fill.fees

    def update_from_fill(self, event):
        if event.type == 'FILL':
            self._update_positions_from_fill(event)
            self._update_holdings_from_fill(event)

    def create_equity_curve_dataframe(self):
        """
        Creates a pandas DataFrame from the all_holdings list of dictionaries.
        """
        curve = pd.DataFrame(self.all_holdings)
        curve.set_index('datetime', inplace=True)
        curve['returns'] = curve['total'].pct_change()
        curve['equity_curve'] = (1.0+curve['returns']).cumprod()

        self.equity_curve = curve

    def generate_trade_record(self):
        trades = pd.DataFrame(Trade.to_dict())
        trades['duration'] = trades['close_date'] - trades['open_date']
        trades['returns_long'] = (trades.loc[trades['direction'] == 'LONG', 'close_price'] /
                                  trades.loc[trades['direction'] == 'LONG', 'open_price']) - 1
        trades['returns_short'] = (
            trades.loc[trades['direction'] == 'SHORT', 'open_price'] / trades.loc[trades['direction'] == 'SHORT', 'close_price']) - 1

        trades['win_trades_long'] = trades['returns_long'] > 0
        trades['loss_trades_long'] = trades['returns_long'] <= 0
        trades['win_trades_short'] = trades['returns_short'] > 0
        trades['loss_trades_short'] = trades['returns_short'] <= 0

        self.trades = trades

    def output_summary_stats(self):
        """
        Creates a list of summary statistics for the portfolio.
        """
        total_return = self.equity_curve['equity_curve'][-1]
        returns = self.equity_curve['returns']
        pnl = self.equity_curve['equity_curve']

        sharpe_ratio = create_sharpe_ratio(returns, periods=252*60*6.5)
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)
        self.equity_curve['drawdown'] = drawdown

        trades_avg_duration = floor(
            self.trades['duration'].mean().total_seconds() / 60)
        trades_avg_return = (self.trades['returns_long'].mean(
        ) + self.trades['returns_short'].mean())/2 * 100

        trades_total_win = self.trades['win_trades_long'].sum(
        ) + self.trades['win_trades_short'].sum()
        trades_total_loss = self.trades['loss_trades_short'].sum(
        ) + self.trades['loss_trades_long'].sum()
        trades_win_loss_ratio = trades_total_win / trades_total_loss
        total_trades = len(self.trades)
        trades_win_pct = trades_total_win / total_trades * 100
        trades_loss_pct = trades_total_loss / total_trades * 100

        stats = [("Total Return", "%0.2f%%" %
                  ((total_return - 1.0) * 100.0)),
                 ("Avg Return (%)", trades_avg_return),
                 ("Avg Trade Duration (min)", trades_avg_duration),
                 ("Total win trades", trades_total_win),
                 ("Total loss trades", trades_total_loss),
                 ("Win/Loss Ratio", trades_win_loss_ratio),
                 ("% Wins", trades_win_pct),
                 ("% Losses", trades_loss_pct),
                 ("Sharpe Ratio", "%0.2f" % sharpe_ratio),
                 ("Max Drawdown", "%0.2f%%" % (max_dd * 100.0)),
                 ("Drawdown Duration", "%d" % dd_duration)]

        dir_path = f'{Path().absolute()}/backtest_results'

        self.equity_curve.to_csv(f'{dir_path}/equity.csv')
        self.trades.to_csv(f'{dir_path}/trades.csv')

        return stats
