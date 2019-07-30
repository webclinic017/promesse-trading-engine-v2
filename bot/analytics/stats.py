import redis
import argparse
from helpers import load_config


def get_balance():
    pass


def get_profit():
    pass


def get_performances():
    pass


def get_trades():
    pass


parser = argparse.ArgumentParser(
    description="Get statistics about current live strategy")

parser.add_argument('-b',
                    '--balance',
                    action='store_true',
                    help='Display current balance in $')

parser.add_argument('-ot',
                    '--opentrades',
                    action='store_true',
                    help='Display current open trades')


args = parser.parse_args()

if args.balance:
    r = redis.Redis()
    balance = {
        'total': r.get('total').decode("utf-8"),
        'cash': r.get('cash').decode("utf-8")
    }

    print(
        f"""Balance:
        - Total: ${balance['total']}
        - Cash: ${balance['cash']}
        """
    )

if args.opentrades:
    symbol_list = load_config()['symbol_list']
    r = redis.Redis()
    for symbol in symbol_list:
        is_open = int(r.hget(f'symbol:{symbol}', 'is_open').decode('utf-8'))
        if is_open:
            open_price = r.hget(
                f'symbol:{symbol}', 'open_price').decode('utf-8')
            current_value = r.hget(
                f'symbol:{symbol}', 'current_value').decode('utf-8')

            print(
                f'{symbol}: $ {current_value} (current value) – $ {open_price} (open price)')
    else:
        print('No open position.')
