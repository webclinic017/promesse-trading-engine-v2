class Trade:

    trades = list()

    def __init__(self, symbol, open_market_price, open_date, open_price, open_fees):
        self.symbol = symbol
        self.open_market_price = open_market_price
        self.is_open = True

        self.open_price = open_price
        self.open_date = open_date
        self.open_fees = open_fees

        self.close_market_price = None
        self.close_price = None
        self.close_date = None
        self.close_fees = None

        self.trades.append(self)

    @classmethod
    def close(self, open_date, close_market_price, close_date, close_price, close_fees):
        trade = [trade for trade in self.trades if trade.open_date
                 == open_date and trade.is_open][0]
        trade.is_open = False
        trade.close_market_price = close_market_price
        trade.close_price = close_price
        trade.close_date = close_date
        trade.close_fees = close_fees

    @classmethod
    def to_dict(self):
        trades = list()
        for trade in Trade.trades:
            trades.append(
                {
                    'symbol': trade.symbol,
                    'open_market_price': trade.open_market_price,
                    'close_market_price': trade.close_market_price,
                    'is_open': trade.is_open,
                    'open_price': trade.open_price,
                    'open_date': trade.open_date,
                    'close_price': trade.close_price,
                    'close_date': trade.close_date
                }
            )
        return trades
