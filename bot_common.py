import datetime
import random
import traceback

import requests

import config
from util import remove_prefix


PRINTER_SERIAL_PORT = '/dev/ttyS9'


def send_message_to_printer(message):
    with open(PRINTER_SERIAL_PORT, 'w') as f:
        f.write(f'{message.user}: {message.text}\n')


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
        command_name
        for command_name in all_command_names
    ]
    general_command_names = [
        self.command_prefix + command_name
        for command_name in all_command_names
        if command_name not in self.modonly_commands
    ]
    modonly_command_names = [
        self.command_prefix + command_name
        for command_name in all_command_names
        if command_name in self.modonly_commands
    ]
    text = f'@{message.user} ' + \
        'Commands: ' + ' '.join(general_command_names) + ' ' + \
        'Mod-only commands: ' + ' '.join(modonly_command_names)
    self.send_privmsg(message.channel, text)


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
