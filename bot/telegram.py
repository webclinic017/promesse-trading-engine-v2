import requests


class TelegramBot:
    def __init__(self, bot_token, channel_id):
        self.bot_token = bot_token
        self.channel_id = channel_id

    def _parse_signal(self, signal):

        parsed_text = f'''
<b>Symbol:</b> <code>{signal['symbol']}</code>
<b>Divergence:</b> <code>{signal['div_type']}</code>
<b>Peak 1:</b> <code>{signal['peaks'][0][0]}</code>
<b>Peak 2:</b> <code>{signal['peaks'][1][0]}</code>
        '''

        return parsed_text

    def send_text(self, message):
        message = self._parse_signal(message)
        send_text = f'https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.channel_id}&text={message}&parse_mode=HTML'
        response = requests.get(send_text)

        return response.json()
