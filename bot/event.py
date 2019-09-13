from __future__ import print_function


class Event:
    """
    Event is base class providing an interface for all subsequent (inherited) events, that will trigger further events in the
    trading infrastructure. 
    """
    pass


class MarketEvent(Event):
    """
    Handles the event of receiving a new market update with
    corresponding bars.
    """

    def __init__(self):
        self.type = 'MARKET'


class SignalEvent(Event):
    """
    Handles the event of sending a Signal from a Strategy object. This is received by a Portfolio object and acted upon.
    """

    def __init__(self, *, strategy_id=1, symbol, datetime, signal_type, strength=1, indicators=None):
        """
        Parameters:
            strategy_id: The unique identifier for the strategy that
            generated the signal. 

            symbol: The ticker symbol, e.g. ’ETH/BTC’.

            datetime: The timestamp at which the signal was generated.

            signal_type: 'LONG' or 'SHORT'.

            strength: An adjustment factor "suggestion" used to scale
            quantity at the portfolio level. Useful for pairs strategies.
        """

        self.type = 'SIGNAL'
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type
        self.strength = strength
        self.indicators = indicators


class OrderEvent(Event):
    """
    Handles the event of sending an Order to an execution system.
    The order contains a symbol (e.g. ETH/BTC), a type (market or limit), quantity and a direction.
    """

    def __init__(self, symbol, order_type, quantity, fill_cost, direction):
        """
        Initialises the order type, setting whether it is
        a Market order (’MKT’) or Limit order (’LMT’), has
        a quantity (integral) and its direction (’BUY’ or
        ’SELL’).

        Parameters:
        symbol: The instrument to trade.
        order_type: ’MKT’ or ’LMT’ for Market or Limit.
        quantity: Non-negative integer for quantity.
        direction: ’BUY’ or ’SELL’ for long or short.
        """

        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost

    def print_order(self):
        """
        Output the values within the Order
        """

        print(
            f'Order: Symbol={self.symbol}, Type={self.type}, Quantity={self.quantity}, Direction={self.direction}')


class FillEvent(Event):
    """
    Encapsulates the notion of a Filled Order, as returned
    from an exchange. Stores the quantity of an instrument
    actually filled and at what price. In addition, stores
    the commission of the trade from the exchange
    """

    def __init__(self, timeindex, symbol, exchange, quantity, direction, fill_cost):
        """       
        Parameters:
            timeindex: The bar-resolution when the order was filled.
            symbol: The instrument which was filled.
            exchange: The exchange where the order was filled.
            quantity: The filled quantity.
            direction: The direction of fill (’BUY’ or ’SELL’)
            fill_cost: The holdings value in dollars.
            fees: An optional commission sent from the exchange
        """

        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost
        self.fees_rate = 0.0
        self.fees = self.fees_rate * self.fill_cost * self.quantity
