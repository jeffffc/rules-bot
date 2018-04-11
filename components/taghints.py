from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler, run_async

import const
import util

HINTS = {
    '#inline': {
        'message': f"Consider using me in inline-mode 😎\n`@{const.SELF_BOT_NAME} {{query}}`",
        'default': "Your search terms",
        'buttons': [{
            'text': '🔎 Try it out',
            'switch_inline_query': '{query}'
        }],
        'help': 'Give a query that will be used for a `switch_to_inline`-button'
    },
    '#private': {
        'message': "Please don't spam the group with {query}, and go to a private "
                   "chat with me instead. Thanks a lot, the other members will appreciate it 😊",
        'default': 'searches or commands',
        'buttons': [{
            'text': '🤖 Go to private chat',
            'url': "https://t.me/{}".format(const.SELF_BOT_NAME)
        }],
        'help': 'Tell a member to stop spamming and switch to a private chat',
    }
}


@run_async
def list_available_hints(bot, update):
    message = "You can use the following hashtags to guide new members:\n\n"
    message += '\n'.join(
        '🗣 {tag} ➖ {help}'.format(
            tag=k, help=v['help']
        ) for k, v in HINTS.items()
    )
    message += "\n\nMake sure to reply to another message, so I know who to refer to."
    update.effective_message.reply_text(message, parse_mode='markdown',
                                        disable_web_page_preview=True)


def get_hint_data(text):
    for k, v in HINTS.items():
        if k not in text:
            continue

        text = text.replace(k, '')
        query = text.strip()

        reply_markup = None
        if v.get('buttons'):
            # Replace 'query' placeholder and expand kwargs
            buttons = [InlineKeyboardButton(
                **{k: v.format(query=query) for k, v in b.items()}
            ) for b in v.get('buttons')]
            reply_markup = InlineKeyboardMarkup(util.build_menu(buttons, 1))

        # Add default value if necessary
        msg = v['message'].format(
            query=query if query else v['default'] if v.get('default') else '')
        return msg, reply_markup, k
    return None, None, None


@run_async
def hint_handler(bot, update):
    text = update.message.text
    reply_to = update.message.reply_to_message

    msg, reply_markup, _ = get_hint_data(text)

    if msg is not None:
        update.effective_message.reply_text(msg,
                                            reply_markup=reply_markup,
                                            reply_to_message_id=reply_to.message_id if reply_to else None,
                                            parse_mode='Markdown',
                                            disable_web_page_preview=True)
        try:
            update.effective_message.delete()
        except BadRequest:
            pass


def register(dispatcher):
    for hashtag in HINTS.keys():
        dispatcher.add_handler(RegexHandler(r'{}.*'.format(hashtag), hint_handler))
    dispatcher.add_handler(CommandHandler(('hints', 'listhints'), list_available_hints))
