import queue

from math import floor
import numpy as np
import pandas as pd
from performance import create_sharpe_ratio, create_drawdowns

from event import OrderEvent, FillEvent


class Portfolio:
    """
    The Portfolio class handles the positions and market value of all instruments at a resolution of a "bar", i.e. secondly, minutely, 5-min, 30-min, 60 min.
    The positions dict stores a time-index of the quantity of positions held.
    The holdings dict stores the cash and total market holdings value of each symbol for a particular time-index, as well as the percentage change in portfolio total across bars.
    """

    def __init__(self, events, data_handler, start_date, initial_capital):
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
        self.pct_capital_risk = 1

        # Risk Management
        self.pct_stop_loss = 0.02
        self.pct_take_profit = 0.05

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
                'open_price': 0.0,
                'current_value': 0.0,
                'is_open': False,
                'trailing_sl': 0.0
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

    def init_trailing_ls(self, symbol, open_price, pct_sl, pct_tp):
        trailing_dict = dict()
        trailing_dict[symbol] = open_price*(1-pct_sl)

        def update_sl(current_value):
            returns = (current_value / open_price) - 1
            current_trailing_sl = 0.0

            if returns >= pct_tp:
                current_trailing_sl = current_value*(1-pct_sl)
            trailing_dict[symbol] = max(
                trailing_dict[symbol], current_trailing_sl)
            return trailing_dict[symbol]

        return update_sl

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
                'open_price': 0.0,
                'current_value': 0.0,
                'is_open': False,
                'trailing_sl': 0.0
            }
            for symbol in self.symbol_list
        }
        holdings['datetime'] = datetime
        holdings['cash'] = holdings['total'] = self.current_holdings['cash']
        holdings['fees'] = self.current_holdings['fees']

        for symbol in self.symbol_list:
            current_position = self.current_positions[symbol]
            current_price = self.data_handler.get_latest_bar(symbol).close
            market_value = current_position * current_price

            holdings[symbol]['current_value'] = market_value
            holdings[symbol]['open_price'] = self.current_holdings[symbol]['open_price']
            holdings[symbol]['is_open'] = self.current_holdings[symbol]['is_open']
            holdings['total'] += market_value

        self.all_holdings.append(holdings)

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

        order_type = 'MKT'

        current_quantity = self.current_positions[symbol]
        fill_cost = self.data_handler.get_latest_bar(symbol).close

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
        if fill.direction == 'BUY':
            fill_dir = 1
        elif fill.direction == 'SELL':
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
            self.current_holdings[fill.symbol]['open_price'] = cost
            self.current_holdings[fill.symbol]['is_open'] = True
            self.current_holdings[fill.symbol]['trailing_sl'] = self.init_trailing_ls(
                fill.symbol,
                cost,
                self.pct_stop_loss,
                self.pct_take_profit
            )
            self.current_holdings['cash'] -= (cost + fill.fees)
            self.current_holdings['total'] -= (cost + fill.fees)

        elif fill.direction == 'SELL':
            self.current_holdings[fill.symbol]['current_value'] -= cost
            self.current_holdings[fill.symbol]['open_price'] = cost
            self.current_holdings[fill.symbol]['is_open'] = False
            self.current_holdings['cash'] += (cost - fill.fees)
            self.current_holdings['total'] += (cost - fill.fees)

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

        stats = [("Total Return", "%0.2f%%" %
                  ((total_return - 1.0) * 100.0)),
                 ("Sharpe Ratio", "%0.2f" % sharpe_ratio),
                 ("Max Drawdown", "%0.2f%%" % (max_dd * 100.0)),
                 ("Drawdown Duration", "%d" % dd_duration)]

        self.equity_curve.to_csv('equity.csv')

        return stats
