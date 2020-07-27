#!/usr/bin/env python
import socket
import json
import datetime
from collections import namedtuple

import config


Message = namedtuple(
    'Message',
    'prefix user channel irc_command irc_args text text_command text_args',
)


def remove_prefix(string, prefix):
    if not string.startswith(prefix):
        return string
    return string[len(prefix):]


class Bot:
    def __init__(self):
        self.irc_server = 'irc.twitch.tv'
        self.irc_port = 6667
        self.oauth_token = config.OAUTH_TOKEN
        self.username = 'squishymcbotty'
        self.command_prefix = '!'
        self.channels = ['clumsycomputer']
        self.template_commands_filename = 'data/template_commands.json'
        self.state_filename = 'data/state.json'
        self.verbose = True
        self.state = {}
        self.template_commands = {}
        self.custom_commands = {
            'date': self.reply_with_date,
            'bigbrain': self.increment_bigbrain,
            'smallbrain': self.increment_smallbrain,
            'cmds': self.list_commands,
            'addcmd': self.add_template_command,
            'editcmd': self.edit_template_command,
            'delcmd': self.delete_template_command,
        }

    def init(self):
        self.read_state()
        self.read_template_commands()
        self.connect()

    def read_state(self):
        with open(self.state_filename, 'r') as file:
            self.state = json.load(file)

    def write_state(self):
        with open(self.state_filename, 'w') as file:
            json.dump(self.state, file)

    def read_template_commands(self):
        with open(self.template_commands_filename, 'r') as file:
            self.template_commands = json.load(file)

    def write_template_commands(self):
        with open(self.template_commands_filename, 'w') as file:
            json.dump(self.template_commands, file)

    def send_privmsg(self, channel, text):
        self.send_command(f'PRIVMSG #{channel} :{text}')

    def send_command(self, command):
        if self.verbose and 'PASS' not in command:
            print(f'< {command}')
        self.irc.send((command + '\r\n').encode())

    def connect(self):
        self.irc = socket.socket()
        self.irc.connect((self.irc_server, self.irc_port))
        self.send_command(f'PASS {self.oauth_token}')
        self.send_command(f'NICK {self.username}')
        for channel in self.channels:
            self.send_command(f'JOIN #{channel}')
            self.send_privmsg(channel, 'Hey there!')
        self.loop_for_messages()

    def get_user_from_prefix(self, prefix):
        domain = prefix.split('!')[0]
        if domain.endswith('.tmi.twitch.tv'):
            return domain.replace('.tmi.twitch.tv', '')
        if 'tmi.twitch.tv' not in domain:
            return domain
        return None

    def parse_message(self, received_msg):
        parts = received_msg.split(' ')

        prefix = None
        user = None
        channel = None
        text = None
        text_command = None
        text_args = None
        irc_command = None
        irc_args = None

        if parts[0].startswith(':'):
            prefix = remove_prefix(parts[0], ':')
            user = self.get_user_from_prefix(prefix)
            parts = parts[1:]

        text_start = next(
            (idx for idx, part in enumerate(parts) if part.startswith(':')),
            None
        )
        if text_start is not None:
            text_parts = parts[text_start:]
            text_parts[0] = text_parts[0][1:]
            text = ' '.join(text_parts)
            text_command = remove_prefix(text_parts[0], self.command_prefix)
            text_args = text_parts[1:]
            parts = parts[:text_start]

        irc_command = parts[0]
        irc_args = parts[1:]

        hash_start = next(
            (idx for idx, part in enumerate(irc_args) if part.startswith('#')),
            None
        )
        if hash_start is not None:
            channel = irc_args[hash_start][1:]

        message = Message(
            prefix=prefix,
            user=user,
            channel=channel,
            text=text,
            text_command=text_command,
            text_args=text_args,
            irc_command=irc_command,
            irc_args=irc_args,
        )

        return message

    def handle_template_command(self, message, template):
        try:
            text = template.format(**{'message': message})
            self.send_privmsg(message.channel, text)
        except IndexError as e:
            text = f"@{message.user} Your command is missing some arguments!"
            self.send_privmsg(message.channel, text)
        except Exception as e:
            # NOTE: Something went wrong here, but as this is a template,
            # things can break, so we'll just print a message and move
            # on. Maybe a better solution to this in the future would be
            # good.
            print('Error while handling template command.', template)
            print(e)

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

        if command_name in self.template_commands and not force:
            text = f"@{message.user} Command {command_name} already exists, use {self.command_prefix}editcmd if you'd like to edit it."
            self.send_privmsg(message.channel, text)
            return

        self.template_commands[command_name] = template
        self.write_template_commands()
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

        if not all([item in valid for item in input]):
            text = f"@{message.user} One of the commands you wrote doesn't exist!"
            self.send_privmsg(message.channel, text)
            return

        for command_name in command_names:
            del self.template_commands[command_name]

        self.write_template_commands()
        if len(command_names) > 1:
            text = f'@{message.user} Commands deleted! {" ".join(command_names)}'
        else:
            text = f'@{message.user} Command {command_names[0]} deleted!'
        self.send_privmsg(message.channel, text)

    def list_commands(self, message):
        all_command_names = list(self.template_commands.keys()) + \
            list(self.custom_commands.keys())
        all_command_names = [
            self.command_prefix + command_name
            for command_name in all_command_names
        ]
        text = f'@{message.user} ' + ' '.join(all_command_names)
        self.send_privmsg(message.channel, text)

    def increment_bigbrain(self, message):
        if 'bigbrain_counter' not in self.state:
            self.state['bigbrain_counter'] = 0
        self.state['bigbrain_counter'] += 1
        text = f'Big brain moments: {self.state["bigbrain_counter"]}'
        self.send_privmsg(message.channel, text)
        self.write_state()

    def increment_smallbrain(self, message):
        if 'smallbrain_counter' not in self.state:
            self.state['smallbrain_counter'] = 0
        self.state['smallbrain_counter'] += 1
        text = f'Small brain moments: {self.state["smallbrain_counter"]}'
        self.send_privmsg(message.channel, text)
        self.write_state()

    def handle_message(self, received_msg):
        if len(received_msg) == 0:
            return

        message = self.parse_message(received_msg)
        if self.verbose:
            print(f'> {received_msg}')
            # print(f'> {message}')

        if message.irc_command == 'PING':
            self.send_command('PONG :tmi.twitch.tv')

        if message.irc_command == 'PRIVMSG':
            if message.text_command in self.custom_commands:
                self.custom_commands[message.text_command](message)
            elif message.text_command in self.template_commands:
                self.handle_template_command(
                    message,
                    self.template_commands[message.text_command],
                )

    def loop_for_messages(self):
        while True:
            received_msgs = self.irc.recv(2048).decode()
            for received_msg in received_msgs.split('\r\n'):
                self.handle_message(received_msg)


def main():
    bot = Bot()
    bot.init()


if __name__ == '__main__':
    main()
