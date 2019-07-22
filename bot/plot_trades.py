import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from time import time
from datetime import datetime
import pandas as pd

sns.set(style="ticks")

dir_path = f'{Path().absolute()}/backtest_results'

trades = pd.read_csv(f'{dir_path}/trades.csv', header=0,
                     parse_dates=True, index_col=0)
columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
data = pd.read_csv(f'{Path().absolute()}/exchange_data/BTC-USDT_1h.csv',
                   header=None, index_col=0, names=columns)
data.index = pd.to_datetime(data.index, unit='ms')
data = data.drop_duplicates()

trades['open_date'] = pd.to_datetime(trades['open_date'])
trades['close_date'] = pd.to_datetime(trades['close_date'])
fig = plt.figure(figsize=(70, 10))
ax1 = fig.add_subplot(111, ylabel='BTC/USDT')
data['close'].plot(ax=ax1, lw=2.)
ax1.plot(trades['open_date'], trades['open_market_price'],
         '^', markersize=10, color='g')
ax1.plot(trades['close_date'], trades['close_market_price'],
         'v', markersize=10, color='r')

plt.show()
