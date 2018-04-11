from urllib.error import HTTPError
from urllib.request import urlopen

from bs4 import BeautifulSoup

from telegram import ParseMode

ARROW_CHARACTER = '➜'
GITHUB_URL = "https://github.com/"
DEFAULT_REPO = 'LonamiWebs/Telethon'


def get_reply_id(update):
    if update.message and update.message.reply_to_message:
        return update.message.reply_to_message.message_id
    return None


def reply_or_edit(bot, update, chat_data, text):
    if update.edited_message:
        chat_data[update.edited_message.message_id].edit_text(text,
                                                              parse_mode=ParseMode.MARKDOWN,
                                                              disable_web_page_preview=True)
    else:
        issued_reply = get_reply_id(update)
        if issued_reply:
            chat_data[update.message.message_id] = bot.sendMessage(update.message.chat_id, text,
                                                                   reply_to_message_id=issued_reply,
                                                                   parse_mode=ParseMode.MARKDOWN,
                                                                   disable_web_page_preview=True)
        else:
            chat_data[update.message.message_id] = update.message.reply_text(text,
                                                                             parse_mode=ParseMode.MARKDOWN,
                                                                             disable_web_page_preview=True)


def get_web_page_title(url):
    try:
        soup = BeautifulSoup(urlopen(url), "html.parser")
        return soup.title.string
    except HTTPError:
        return None


def get_text_not_in_entities(html):
    soup = BeautifulSoup(html, 'html.parser')
    return ' '.join(soup.find_all(text=True, recursive=False))


def build_menu(buttons,
               n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu
