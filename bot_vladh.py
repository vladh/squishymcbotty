import config
from bot import Bot
import bot_common


def main():
    custom_commands = {
        'date': bot_common.reply_with_date,
        'cmds': bot_common.list_commands,
        'addcmd': bot_common.add_template_command,
        'editcmd': bot_common.edit_template_command,
        'delcmd': bot_common.delete_template_command,
        'addquote': bot_common.add_quote,
        'quote': bot_common.reply_with_quote,
        'weather': bot_common.get_weather,
        'join': bot_common.add_to_join_list,
        'clearjoinlist': bot_common.clear_join_list,
        'getrandomjoiner': bot_common.get_random_joiner,
    }
    bot = Bot(
        custom_commands=custom_commands,
        oauth_token=config.OAUTH_TOKEN,
        username='squishymcbotty',
        command_prefix='!',
        channels=['vladh'],
        caps=[':twitch.tv/tags'],
        state_filename='data/state_vladh.json',
        state_schema={
            'template_commands': {},
            'quotes': [],
            'joinlist': [],
        },
        modonly_commands=[
            'addcmd', 'editcmd', 'delcmd',
            'addquote', 'noot',
            'clearjoinlist', 'getrandomjoiner',
        ],
    )
    bot.init()


if __name__ == '__main__':
    main()
