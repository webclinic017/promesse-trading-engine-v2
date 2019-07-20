class Trade:

    trades = list()

    def __init__(self, id, symbol, is_open, open_price, open_date, open_fees, timeframe, strategy):
        self.id = id
        self.symbol = symbol
        self.is_open = is_open

        self.open_price = open_price
        self.open_date = open_date
        self.open_fees = open_fees

        self.close_price = None
        self.close_date = None
        self.close_fees = None

        self.timeframe = timeframe
        self.strategy = strategy

        Trade.trades.append(self)

    def close(self, id):
        Trade.trades
