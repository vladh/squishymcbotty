#!/usr/bin/env python
from collections import namedtuple
from pprint import pprint
import json
import socket
import ssl
import traceback

from util import remove_prefix


Message = namedtuple(
    'Message',
    'prefix user channel irc_command irc_args text text_command text_args tags',
)


class Bot:
    def __init__(
        self, custom_commands, oauth_token, username, command_prefix,
        channels, state_filename, caps=[], state_schema={},
        modonly_commands=[], verbose=True,
    ):
        self.irc_server = 'irc.chat.twitch.tv'
        self.irc_port = 6697
        self.oauth_token = oauth_token
        self.username = username
        self.command_prefix = command_prefix
        self.channels = channels
        self.caps = caps
        self.state_filename = state_filename
        self.verbose = verbose
        self.state = {}
        self.state_schema = state_schema
        self.custom_commands = custom_commands
        self.modonly_commands = modonly_commands

    def init(self):
        self.read_state()
        self.connect()

    def ensure_state_schema(self):
        is_dirty = False
        for key in self.state_schema:
            if key not in self.state:
                is_dirty = True
                self.state[key] = self.state_schema[key]
        return is_dirty

    def read_state(self):
        with open(self.state_filename, 'r') as file:
            self.state = json.load(file)
        is_dirty = self.ensure_state_schema()
        if is_dirty:
            self.write_state()

    def write_state(self):
        with open(self.state_filename, 'w') as file:
            json.dump(self.state, file)

    def send_privmsg(self, channel, text):
        if text.startswith('/'):
            return
        self.send_command(f'PRIVMSG #{channel} :{text}')

    def send_command(self, command):
        if self.verbose and 'PASS' not in command:
            print(f'< {command}')
        self.irc.send((command + '\r\n').encode())

    def connect(self):
        self.irc = ssl.wrap_socket(socket.socket())
        self.irc.connect((self.irc_server, self.irc_port))
        self.send_command(f'PASS {self.oauth_token}')
        self.send_command(f'NICK {self.username}')
        if len(self.caps) > 0:
            self.send_command(f'CAP REQ {" ".join(self.caps)}')
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
        tags = None

        if parts[0].startswith('@'):
            tag_text = remove_prefix(parts[0], '@')
            tag_parts = tag_text.split(';')
            split_tag_parts = [
                tag_part.split('=')
                for tag_part in tag_parts
            ]
            tags = {
                tag_name: tag_value
                for tag_name, tag_value in split_tag_parts
            }
            parts = parts[1:]

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
            if text_parts[0].startswith(self.command_prefix):
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
            tags=tags,
        )

        return message

    def handle_template_command(self, message, template):
        try:
            text = template.format(**{'message': message})
            self.send_privmsg(message.channel, text)
        except IndexError:
            text = f"@{message.user} Your command is missing some arguments!"
            self.send_privmsg(message.channel, text)
        except Exception:
            # NOTE: Something went wrong here, but as this is a template,
            # things can break, so we'll just print a message and move
            # on. Maybe a better solution to this in the future would be
            # good.
            print('Error while handling template command.', template)
            traceback.print_exc()

    def is_mod(self, message):
        return 'broadcaster' in message.tags['badges'] or \
            message.tags['mod'] == '1'

    def handle_message(self, received_msg):
        if len(received_msg) == 0:
            return

        message = self.parse_message(received_msg)
        if self.verbose:
            print(f'> ({message.irc_command} {message.irc_args}) @{message.user}: {message.text}')

        if message.irc_command == 'PING':
            self.send_command('PONG :tmi.twitch.tv')

        if message.irc_command == 'PRIVMSG':
            if message.text_command in self.modonly_commands and not self.is_mod(message):
                return
            if message.text_command in self.custom_commands:
                self.custom_commands[message.text_command](self, message)
            elif message.text_command in self.state['template_commands']:
                self.handle_template_command(
                    message,
                    self.state['template_commands'][message.text_command],
                )

    def loop_for_messages(self):
        while True:
            received_msgs = self.irc.recv(2048).decode()
            for received_msg in received_msgs.split('\r\n'):
                self.handle_message(received_msg)
