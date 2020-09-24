import config
from bot import Bot
import bot_common


IS_PRINTER_ENABLED = False


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


def on_message(self, message):
    if IS_PRINTER_ENABLED and message.irc_command == 'PRIVMSG':
        bot_common.send_message_to_printer(message)


def main():
    custom_commands = {
        'date': bot_common.reply_with_date,
        'bigbrain': increment_bigbrain,
        'smallbrain': increment_smallbrain,
        'cmds': bot_common.list_commands,
        'addcmd': bot_common.add_template_command,
        'editcmd': bot_common.edit_template_command,
        'delcmd': bot_common.delete_template_command,
        'addquote': bot_common.add_quote,
        'quote': bot_common.reply_with_quote,
        'weather': bot_common.get_weather,
    }
    bot = Bot(
        custom_commands=custom_commands,
        oauth_token=config.OAUTH_TOKEN,
        username='squishymcbotty',
        command_prefix='!',
        channels=['clumsycomputer'],
        caps=[':twitch.tv/tags'],
        state_filename='data/state_clumsycomputer.json',
        event_handlers={
            'on_message': on_message,
        },
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
