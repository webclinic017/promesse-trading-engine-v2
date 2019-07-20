from data_handler.csv_data_handler import CSVDataHandler
from portfolio import Portfolio
from strategy.pprsi import PPRSI
from execution_handler import SimulatedExecutionHandler
from backtest import Backtest

from datetime import datetime

symbol_list = ['BTC-USDT']

backtest = Backtest(
    csv_dir='exchange_data',
    symbol_list=symbol_list,
    timeframe='1h',
    start_date=datetime(2017, 7, 18),
    initial_capital=100,
    DataHandler=CSVDataHandler,
    Portfolio=Portfolio,
    Strategy=PPRSI,
    ExecutionHandler=SimulatedExecutionHandler
)

backtest.simulate_trading()
