from portfolio import Portfolio
from strategy.pprsi import PPRSI
from execution_handler import SimulatedExecutionHandler
from engine import Engine

from datetime import datetime
from helpers import load_config

config = load_config()

if config['run_mode'] == 'backtest':
    from data_handler.csv_data_handler import CSVDataHandler as DataHandler
    heartbeat = 0
    start_date = datetime(2017, 1, 1)

else:
    from data_handler.live_data_handler import LiveDataHandler as DataHandler
    heartbeat = config['heartbeat']
    start_date = datetime.utcnow()

symbol_list = config['symbol_list']
timeframe = config['timeframe']
initial_capital = config['initial_capital']

engine = Engine(
    symbol_list=symbol_list,
    timeframe=timeframe,
    heartbeat=heartbeat,
    start_date=start_date,
    initial_capital=initial_capital,
    DataHandler=DataHandler,
    Portfolio=Portfolio,
    Strategy=PPRSI,
    ExecutionHandler=SimulatedExecutionHandler
)

engine.start()
