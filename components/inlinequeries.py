from uuid import uuid4

from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode
from telegram.ext import InlineQueryHandler, run_async

from components import taghints
from rules_bot import fuzzy_replacements_markdown
from search import search, DOCS_URL


def article(title='', description='', message_text=''):
    return InlineQueryResultArticle(
        id=uuid4(),
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=message_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True)
    )


def hint_article(msg, reply_markup, key):
    return InlineQueryResultArticle(
        id=key,
        title='Send hint on {}'.format(key.capitalize()),
        input_message_content=InputTextMessageContent(
            message_text=msg,
            parse_mode="Markdown",
            disable_web_page_preview=True
        ),
        reply_markup=reply_markup
    )


@run_async
def inline_query(bot, update, all_list, threshold=20):
    query = update.inline_query.query
    results_list = list()

    if len(query) > 0:

        msg, reply_markup, key = taghints.get_hint_data(query)
        if msg is not None:
            results_list.append(hint_article(msg, reply_markup, key))

        modified, replaced = fuzzy_replacements_markdown(query)
        if modified:
            results_list.append(article(
                title="Replace links",
                description=', '.join(modified),
                message_text=replaced))

        docs = search.docs(query, threshold=threshold)

        if docs:
            for doc in docs:
                text = f'*{doc.short_name}*\n' \
                       f'_Telethon_ documentation for this {doc.type}:\n' \
                       f'[{doc.full_name}]({doc.url})'

                results_list.append(article(
                    title=f'{doc.full_name}',
                    description="Telethon documentation",
                    message_text=text,
                ))

        api_docs = search.api_docs(query, all_list)

        if api_docs:
            for doc in api_docs:
                text = f'*{doc.short_name}*\n' \
                       f'_Telethon_ API Docs for this {doc.type}:\n' \
                       f'[{doc.full_name}]({doc.url})'

                results_list.append(article(
                    title=f'{doc.full_name}',
                    description="Telethon API Details",
                    message_text=text,
                ))

        # "No results" entry
        if len(results_list) == 0:
            results_list.append(article(
                title='❌ No results.',
                description='',
                message_text=f'Click [here]({DOCS_URL}) to see the full documentation of _Telethon_',
            ))

    else:  # no query input
        results_list = list()
        results_list.append(article(
            title='❌ No results.',
            description='',
            message_text=f'Click [here]({DOCS_URL}) to see the full documentation of _Telethon_',
        ))

    bot.answerInlineQuery(update.inline_query.id, results=results_list, switch_pm_text='Help',
                          switch_pm_parameter='inline-help')


def register(dispatcher, all_list):
    dispatcher.add_handler(InlineQueryHandler(lambda bot, update: inline_query(bot, update, all_list)))
