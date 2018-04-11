import configparser
import logging
import os
import re
import time
import json
from functools import lru_cache

from telegram import Bot, ParseMode, MessageEntity, ChatAction
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler, Updater, MessageHandler, Filters, run_async
from telegram.utils.helpers import escape_markdown

import const
from components import inlinequeries, taghints
from const import ENCLOSED_REGEX, ENCLOSING_REPLACEMENT_CHARACTER, GITHUB_PATTERN, OFFTOPIC_CHAT_ID, OFFTOPIC_RULES, \
    OFFTOPIC_USERNAME, ONTOPIC_RULES, ONTOPIC_USERNAME
from search import search
from util import ARROW_CHARACTER, DEFAULT_REPO, GITHUB_URL, get_reply_id, reply_or_edit, get_web_page_title, \
    get_text_not_in_entities

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

self_chat_id = '@'  # Updated in main()


@run_async
def start(bot, update, args=None):
    if args:
        if args[0] == 'inline-help':
            inlinequery_help(bot, update)
    elif update.message.chat.username not in (OFFTOPIC_USERNAME, ONTOPIC_USERNAME):
        update.message.reply_text("Hi. I'm a bot that will announce the rules of the "
                                  "Telethon groups when you type /rules.")


@run_async
def inlinequery_help(bot, update):
    chat_id = update.message.chat_id
    char = ENCLOSING_REPLACEMENT_CHARACTER
    text = (f"Use the `{char}`-character in your inline queries and I will replace "
            f"them with a link to the corresponding article from the documentation.\n\n"
            f"*Example:*\n"
            f"{SELF_CHAT_ID} I 💙 {char}TelegramClient{char} and you can receive {char}NewMessage{char} with it.\n\n"
            f"*becomes:*\n"
            f"I 💙 [telegram_client.TelegramClient](https://telethon.readthedocs.io/en/latest/telethon.html#"
            f"telethon.telegram_client.TelegramClient), and you can receive [events.NewMessage]("
            f"https://telethon.readthedocs.io/en/latest/telethon.events.html#telethon.events.NewMessage) with it.")
    bot.sendMessage(chat_id, text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


@run_async
def rules(bot, update):
    """Load and send the appropiate rules based on which group we're in"""
    if update.message.chat.username == ONTOPIC_USERNAME:
        update.message.reply_text(ONTOPIC_RULES, parse_mode=ParseMode.HTML,
                                  disable_web_page_preview=True)
    elif update.message.chat.username == OFFTOPIC_USERNAME:
        update.message.reply_text(OFFTOPIC_RULES, parse_mode=ParseMode.HTML,
                                  disable_web_page_preview=True)
    else:
        update.message.reply_text("Hmm. You're not in a Telethon group, "
                                  "and I don't know the rules around here.")


@run_async
def docs(bot, update):
    """ Documentation link """
    text = "You can find our documentation at [Read the Docs](https://telethon.readthedocs.io/en/stable/)"
    if update.message.reply_to_message:
        reply_id = update.message.reply_to_message.message_id
    else:
        reply_id = None
    update.message.reply_text(text, parse_mode='Markdown', quote=False,
                              disable_web_page_preview=True, reply_to_message_id=reply_id)
    update.message.delete()


def off_on_topic(bot, update, groups):
    chat_username = update.message.chat.username
    if chat_username == ONTOPIC_USERNAME and groups[0].lower() == 'off':
        reply = update.message.reply_to_message
        moved_notification = 'I moved this discussion to the ' \
                             '[off-topic Group]({}).'
        if reply and reply.text:
            issued_reply = get_reply_id(update)

            if reply.from_user.username:
                name = '@' + reply.from_user.username
            else:
                name = reply.from_user.first_name

            replied_message_text = reply.text
            replied_message_id = reply.message_id

            text = (f'{name} [wrote](t.me/{ONTOPIC_USERNAME}/{replied_message_id}):\n'
                    f'{replied_message_text}\n\n'
                    f'⬇️ ᴘʟᴇᴀsᴇ ᴄᴏɴᴛɪɴᴜᴇ ʜᴇʀᴇ ⬇️')

            offtopic_msg = bot.send_message(OFFTOPIC_CHAT_ID, text, disable_web_page_preview=True,
                                            parse_mode=ParseMode.MARKDOWN)

            update.message.reply_text(
                moved_notification.format(f'https://telegram.me/{OFFTOPIC_USERNAME}/' +
                                          str(offtopic_msg.message_id)),
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=issued_reply
            )

        else:
            update.message.reply_text(
                f'The off-topic group is [here](https://telegram.me/{OFFTOPIC_USERNAME}). '
                'Come join us!',
                disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)

    elif chat_username == OFFTOPIC_USERNAME and groups[0].lower() == 'on':
        update.message.reply_text(
            f'The on-topic group is [here](https://telegram.me/{ONTOPIC_USERNAME}). '
            'Come join us!',
            disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)


@run_async
def sandwich(bot, update, groups):
    if update.message.chat.username == OFFTOPIC_USERNAME:
        if 'sudo' in groups[0]:
            update.message.reply_text("Okay.", quote=True)
        else:
            update.message.reply_text("What? Make it yourself.", quote=True)


@run_async
def keep_typing(last, chat, action):
    now = time.time()
    if (now - last) > 1:
        chat.send_action(action)
    return now


@run_async
@lru_cache()
def _get_github_title_and_type(url, sha=None):
    title = get_web_page_title(url)
    if not title:
        return
    split = title.split(' · ')
    t = 'PR' if 'Pull Request' in split[1] else 'Issue'
    if sha:
        t = 'Commit'
    return split[0], t


@run_async
def github(bot, update, chat_data):
    message = update.message or update.edited_message
    last = 0
    things = {}

    # Due to bug in ptb we need to convert entities of type URL to TEXT_LINK for them to be converted to html
    for entity in message.entities:
        if entity.type == MessageEntity.URL:
            entity.type = MessageEntity.TEXT_LINK
            entity.url = message.parse_entity(entity)

    for match in GITHUB_PATTERN.finditer(get_text_not_in_entities(message.text_html)):
        last = keep_typing(last, update.effective_chat, ChatAction.TYPING)
        logging.debug(match.groupdict())

        user, repo, number, sha = [match.groupdict()[x] for x in ('user', 'repo', 'number', 'sha')]
        url = GITHUB_URL
        name = ''
        if number:
            if user and repo:
                url += f'{user}/{repo}'
                name += f'{user}/{repo}'
            else:
                url += DEFAULT_REPO
            name += f'#{number}'
            url += f'/issues/{number}'
        else:
            if user:
                name += user
                if repo:
                    url += f'{user}/{repo}'
                    name += f'/{repo}'
                name += '@'
            if not repo:
                url += DEFAULT_REPO
            name += sha[:7]
            url += f'/commit/{sha}'

        if url in things.keys():
            continue

        gh = _get_github_title_and_type(url, sha)
        if not gh:
            continue

        name = f'{gh[1]} {name}: {gh[0]}'
        things[url] = name

    if things:
        reply_or_edit(bot, update, chat_data,
                      '\n'.join([f'[{name}]({url})' for url, name in things.items()]))


def fuzzy_replacements_markdown(query, threshold=95):
    """ Replaces the enclosed characters in the query string with hyperlinks to the documentations """
    symbols = re.findall(ENCLOSED_REGEX, query)

    if not symbols:
        return None, None

    replacements = list()
    for s in symbols:
        docs_res = search.docs(s, threshold=threshold)
        if docs_res:
            text = f'[{docs_res[0].short_name}]({docs_res[0].url})'

            replacements.append((docs_res[0].short_name, s, text))
            continue

        # not found
        replacements.append((s + '❓', s, escape_markdown(s)))

    result = query
    for name, symbol, text in replacements:
        char = ENCLOSING_REPLACEMENT_CHARACTER
        result = result.replace(f'{char}{symbol}{char}', text)

    result_changed = [x[0] for x in replacements]
    return result_changed, result


def error(bot, update, err):
    """Log all errors"""
    logger.warning(f'Update "{update}" caused error "{err}"')


def main():
    config = configparser.ConfigParser()
    config.read('bot.ini')

    updater = Updater(token=config['KEYS']['bot_api'])
    dispatcher = updater.dispatcher

    global SELF_CHAT_ID
    SELF_CHAT_ID = f'@{updater.bot.get_me().username}'

    # dump requests list
    with open('resources/search.json', 'r') as file:
        main_list = json.load(file)
        requests_list = [each['value'] for each in
                         main_list['body'][13]['block']['body'][0]['expression']['right']['elements']]
        types_list = [each['value'] for each in
                      main_list['body'][13]['block']['body'][1]['expression']['right']['elements']]
        constructors_list = [each['value'] for each in
                             main_list['body'][13]['block']['body'][2]['expression']['right']['elements']]
        requests_u_list = [each['value'] for each in
                           main_list['body'][13]['block']['body'][3]['expression']['right']['elements']]
        types_u_list = [each['value'] for each in
                        main_list['body'][13]['block']['body'][4]['expression']['right']['elements']]
        constructors_u_list = [each['value'] for each in
                               main_list['body'][13]['block']['body'][5]['expression']['right']['elements']]
        all_list = {"Method": (requests_list, requests_u_list),
                    "Type": (types_list, types_u_list),
                    "Constructor": (constructors_list, constructors_u_list)}

    start_handler = CommandHandler('start', start, pass_args=True)
    rules_handler = CommandHandler('rules', rules)
    rules_handler_hashtag = RegexHandler(r'.*#rules.*', rules)
    docs_handler = CommandHandler('docs', docs, allow_edited=True)
    sandwich_handler = RegexHandler(r'(?i)[\s\S]*?((sudo )?make me a sandwich)[\s\S]*?', sandwich,
                                    pass_groups=True)
    off_on_topic_handler = RegexHandler(r'(?i)[\s\S]*?\b(?<!["\\])(off|on)[- _]?topic\b',
                                        off_on_topic,
                                        pass_groups=True)

    # We need several matches so RegexHandler is basically useless
    # therefore we catch everything and do regex ourselves
    # This should probably be in another dispatcher group
    # but I kept getting SystemErrors...
    github_handler = MessageHandler(Filters.all, github, allow_edited=True, pass_chat_data=True)

    taghints.register(dispatcher)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(rules_handler)
    dispatcher.add_handler(rules_handler_hashtag)
    dispatcher.add_handler(docs_handler)
    dispatcher.add_handler(sandwich_handler)
    dispatcher.add_handler(off_on_topic_handler)
    dispatcher.add_handler(github_handler)

    inlinequeries.register(dispatcher, all_list)
    dispatcher.add_error_handler(error)

    updater.start_polling(clean=True)
    logger.info('Listening...')
    updater.idle()


if __name__ == '__main__':
    main()
