import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from time import time
from datetime import datetime
import pandas as pd

sns.set(style="ticks")

dir_path = f'{Path().absolute()}/backtest_results'

data = pd.read_csv(f'{dir_path}/equity.csv', header=0,
                   parse_dates=True, index_col=0)
data = data.sort_index()

fig = plt.figure(figsize=[40, 20])
fig.patch.set_facecolor('white')

ax1 = fig.add_subplot(311, ylabel='Portfolio value, %')
data['equity_curve'].plot(ax=ax1, color="blue", lw=1.)
plt.grid(True)

ax2 = fig.add_subplot(312, ylabel='Period returns, %')
data['returns'].plot(ax=ax2, color="black", lw=1.)
plt.grid(True)

ax3 = fig.add_subplot(313, ylabel='Drawdowns, %')
data['drawdown'].plot(ax=ax3, color="red", lw=1.)
plt.grid(True)

plt.show()
