from data_handler.live_data_handler import LiveDataHandler
from data_handler.csv_data_handler import CSVDataHandler
from portfolio import Portfolio
from strategy.bbrsi import BBRSI
from execution_handler import SimulatedExecutionHandler
from backtest import Backtest

from datetime import datetime

data = LiveDataHandler('events', 'binance', ['BTC/USDT', 'ETH/USDT'], '1h')
print(data.get_latest_bars_values('BTC/USDT', 'open', N=10))


# symbol_list = ['ETH-BTC']

# backtest = Backtest(
#     csv_dir='exchange_data',
#     symbol_list=symbol_list,
#     timeframe='1h',
#     start_date=datetime(2017, 7, 18),
#     initial_capital=1,
#     DataHandler=CSVDataHandler,
#     Portfolio=Portfolio,
#     Strategy=BBRSI,
#     ExecutionHandler=SimulatedExecutionHandler
# )

# backtest.simulate_trading()
