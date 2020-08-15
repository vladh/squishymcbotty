import datetime
import random
import traceback

import requests

import config
from bot import Bot
from util import remove_prefix


def reply_with_date(self, message):
    formatted_date = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    text = f'Here you go {message.user}, the date is: {formatted_date}.'
    self.send_privmsg(message.channel, text)


def add_template_command(self, message, force=False):
    if len(message.text_args) < 2:
        text = f"@{message.user} Usage: !addcmd <name> <template>"
        self.send_privmsg(message.channel, text)
        return

    command_name = remove_prefix(message.text_args[0], self.command_prefix)
    template = ' '.join(message.text_args[1:])

    if command_name in self.custom_commands:
        text = f"@{message.user} Can't add command {command_name} as it is already a " \
            f"built-in command."
        self.send_privmsg(message.channel, text)
        return

    if command_name in self.state['template_commands'] and not force:
        text = f"@{message.user} Command {command_name} already exists, use " \
            f"{self.command_prefix}editcmd if you'd like to edit it."
        self.send_privmsg(message.channel, text)
        return

    self.state['template_commands'][command_name] = template
    self.write_state()
    text = f'@{message.user} Command {command_name} added!'
    self.send_privmsg(message.channel, text)


def edit_template_command(self, message):
    self.add_template_command(message, force=True)


def delete_template_command(self, message):
    if len(message.text_args) < 1:
        text = f"@{message.user} Usage: !delcmd <name>"
        self.send_privmsg(message.channel, text)
        return

    command_names = [
        remove_prefix(arg, self.command_prefix)
        for arg in message.text_args
    ]

    if not all([
        command_name in self.state['template_commands']
        for command_name in command_names
    ]):
        text = f"@{message.user} One of the commands you wrote doesn't exist!"
        self.send_privmsg(message.channel, text)
        return

    for command_name in command_names:
        del self.state['template_commands'][command_name]

    self.write_state()
    if len(command_names) > 1:
        text = f'@{message.user} Commands deleted! {" ".join(command_names)}'
    else:
        text = f'@{message.user} Command {command_names[0]} deleted!'
    self.send_privmsg(message.channel, text)


def list_commands(self, message):
    all_command_names = list(self.state['template_commands'].keys()) + \
        list(self.custom_commands.keys())
    all_command_names = [
        self.command_prefix + command_name
        for command_name in all_command_names
    ]
    text = f'@{message.user} ' + ' '.join(all_command_names)
    self.send_privmsg(message.channel, text)


def increment_bigbrain(self, message):
    self.state['bigbrain_counter'] += 1
    text = f'Big brain moments: {self.state["bigbrain_counter"]}'
    self.send_privmsg(message.channel, text)
    self.write_state()


def increment_smallbrain(self, message):
    self.state['smallbrain_counter'] += 1
    text = f'Small brain moments: {self.state["smallbrain_counter"]}'
    self.send_privmsg(message.channel, text)
    self.write_state()


def add_quote(self, message):
    if len(message.text_args) < 2:
        text = f"@{message.user} Usage: !addquote <quote>"
        self.send_privmsg(message.channel, text)
        return

    quote = ' '.join(message.text_args)
    quote_idx = len(self.state['quotes'])

    self.state['quotes'].append(quote)
    self.write_state()
    text = f'@{message.user} Quote {quote_idx} added!'
    self.send_privmsg(message.channel, text)


def reply_with_quote(self, message):
    if len(self.state['quotes']) == 0:
        return

    if (
        len(message.text_args) > 0 and
        message.text_args[0].isnumeric() and
        int(message.text_args[0]) < len(self.state['quotes'])
    ):
        quote_idx = int(message.text_args[0])
    else:
        quote_idx = random.randrange(0, len(self.state['quotes']))

    quote = self.state['quotes'][quote_idx]

    text = f'Quote {quote_idx}: {quote}'
    self.send_privmsg(message.channel, text)


def get_weather(self, message):
    try:
        city_name = ' '.join(message.text_args)
        url = f'https://api.openweathermap.org/data/2.5/weather' \
            f'?q={city_name}' \
            f'&appid={config.OPENWEATHER_API_KEY}' \
            f'&units=metric'
        r = requests.get(url)
        weather_data = r.json()

        if weather_data['cod'] != 200:
            text = f'Error while getting weather! {weather_data["message"]}'
            self.send_privmsg(message.channel, text)
            return

        text = f'{weather_data["name"]}, {weather_data["sys"]["country"]}: ' \
            f'{weather_data["weather"][0]["description"]}, ' \
            f'{round(weather_data["main"]["temp"])}C, ' \
            f'feels like {round(weather_data["main"]["feels_like"])}C, ' \
            f'{weather_data["main"]["humidity"]}% humidity, ' \
            f'wind speed {weather_data["wind"]["speed"]}m/s'
        self.send_privmsg(message.channel, text)
    except Exception:
        print('Error while getting weather!')
        traceback.print_exc()


def main():
    custom_commands = {
        'date': reply_with_date,
        'bigbrain': increment_bigbrain,
        'smallbrain': increment_smallbrain,
        'cmds': list_commands,
        'addcmd': add_template_command,
        'editcmd': edit_template_command,
        'delcmd': delete_template_command,
        'addquote': add_quote,
        'quote': reply_with_quote,
        'weather': get_weather,
    }
    bot = Bot(
        custom_commands=custom_commands,
        oauth_token=config.OAUTH_TOKEN,
        username='squishymcbotty',
        command_prefix='!',
        channels=['clumsycomputer'],
        caps=[':twitch.tv/tags'],
        state_filename='data/state.json',
        state_schema={
            'template_commands': {},
            'bigbrain_counter': 0,
            'smallbrain_counter': 0,
            'quotes': [],
        },
        modonly_commands=[
            'addcmd', 'editcmd', 'delcmd',
            'addquote', 'noot',
        ],
    )
    bot.init()


if __name__ == '__main__':
    main()
