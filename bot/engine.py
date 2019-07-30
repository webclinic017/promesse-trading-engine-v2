from __future__ import print_function

import queue
import datetime
import pprint
import time

from helpers import load_config


class Engine:
    def __init__(self, *, symbol_list, timeframe, heartbeat, start_date, initial_capital, DataHandler, Portfolio, Strategy, ExecutionHandler):
        self.symbol_list = symbol_list
        self.timeframe = timeframe
        self.heartbeat = heartbeat
        self.start_date = start_date
        self.initial_capital = initial_capital

        self.config = load_config()

        # Init the event Queue that will orchestrate all the backtesting operations
        # It is used by each component of the trading engine (DataHandler, Strategy, Portfolio, Execution Handler)
        self.events = queue.Queue()

        self.data_handler = DataHandler(
            self.events,
            self.symbol_list,
            self.timeframe
        )

        self.portfolio = Portfolio(
            self.events,
            self.data_handler,
            self.start_date,
            self.initial_capital
        )

        self.stratagy = Strategy(
            self.events,
            self.data_handler,
            self.portfolio
        )

        self.execution_handler = ExecutionHandler(self.events)

        self.signals = 0
        self.orders = 0
        self.fills = 0

    def _run(self):
        """
        It runs the trading bot engine

        1. The outerloop
            - iterates over  all the available data in the Data Handler.
            - Once it hits the end, the loop breaks and the backtesting stops.
            - Each iteration send market data to the other components of the trading engine via the Market Event.
            - The Market Event let the program enter the innerloop

        2. The innerloop
            There are 4 stages in the innerloop, each one get executed depending on the type of the event fired.
            - MARKET
                It tells the trading engine that new data is available and can be processed in the Strategy and Portfolio components.
            - SIGNAL
                Based on strategy conditions, a signal event is generated (Long, Short or Exit) and then sent to the portfolio
            - ORDER
                The portfolio class receives the Signal event, processed it and generates an Order event (buy or sell)
            - FILL
                Once the order is generated, it is sent to the Execution Handler which fills the order. The fill event is sent back to the 
                portfolio to update the current positions and holdings.
        """
        print(f'Running in  {self.config["run_mode"]} mode')
        i = 0
        while True:
            i += 1
            print(i)

            if self.data_handler.continue_backtest:
                self.data_handler.update_bars()
            else:
                break

            while True:
                try:
                    # Get the latest event from the queue
                    event = self.events.get(False)
                except queue.Empty:
                    # When the queue is empty, the innerloop breaks and goes to get new market data
                    break
                else:
                    if event is not None:
                        if event.type == 'MARKET':
                            # First update portoflio positions and holdings
                            self.portfolio.update_all_positions_holdings()
                            # Then, calculate indicators for each symbol using latest market and portfolio values
                            # If the strategy fora giben symbol detects a signal, it triggers an event (SIGNAL) to generate an order from the portfolio
                            self.stratagy.calculate_signals()

                        elif event.type == 'SIGNAL':
                            self.signals += 1
                            self.portfolio.send_order(event)

                        elif event.type == 'ORDER':
                            self.orders += 1
                            self.execution_handler.execute_order(event)

                        elif event.type == 'FILL':
                            self.fills += 1
                            self.portfolio.update_from_fill(event)

            time.sleep(self.heartbeat)

    def _output_performance(self):
        """
        Outputs the strategy performance from the backtest.
        """
        self.portfolio.create_equity_curve_dataframe()
        self.portfolio.generate_trade_record()

        print("Creating summary stats...")
        stats = self.portfolio.output_summary_stats()

        print("Creating equity curve...")
        print(self.portfolio.equity_curve.tail(10))
        pprint.pprint(stats)

        print("Signals: %s" % self.signals)
        print("Orders: %s" % self.orders)
        print("Fills: %s" % self.fills)

    def start(self):
        self._run()
        self._output_performance()
