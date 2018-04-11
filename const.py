import re

ENCLOSING_REPLACEMENT_CHARACTER = '+'
ENCLOSED_REGEX = rf'\{ENCLOSING_REPLACEMENT_CHARACTER}([a-zA-Z_.0-9]*)\{ENCLOSING_REPLACEMENT_CHARACTER}'
OFFTOPIC_USERNAME = 'TelethonChat'
ONTOPIC_USERNAME = 'TelethonOffTopic'
OFFTOPIC_CHAT_ID = '@' + OFFTOPIC_USERNAME
TELEGRAM_SUPERSCRIPT = 'ᵀᴱᴸᴱᴳᴿᴬᴹ'
SELF_BOT_NAME = 'thetelethonbot'
ONTOPIC_RULES = """This group is for questions, answers and discussions around the <a href="https://github.com/LonamiWebs/Telethon">Telethon</a>.

<b>Rules:</b>
- The group language is English
- Read telethon.rtfd.io / lonamiwebs.github.io/Telethon before asking things here!
- Keep this group on topic (issues with Telethon, suggestions, share or discuss problems and enhancements)
- No meta questions (eg. <i>"Can I ask something?"</i>)
- Use a pastebin when you have a question about a long piece of code, like <a href="https://www.hastebin.com">this one</a>.

For off-topic discussions, please use our <a href="https://telegram.me/telethonofftopic">off-topic group</a>."""

OFFTOPIC_RULES = """<b>Topics:</b>
- shitposting
- smol tests

<b>Rules:</b>
- 

ascend <a href='https://t.me/joinchat/A7LmgRHHG0IGxhE71LbfoA'>here</a>, where you won't disturb our leader and you can spam hard"""

GITHUB_PATTERN = re.compile(r'''
    (?i)                                # Case insensitivity
    [\s\S]*?                            # Any characters
    (?:                                 # Optional non-capture group for username/repo
        (?P<user>[^\s/\#@]+)            # Matches username (any char but whitespace, slash, hashtag and at)
        (?:/(?P<repo>[^\s/\#@]+))?      # Optionally matches repo, with a slash in front
    )?                                  # End optional non-capture group
    (?:                                 # Match either
        (
            (?P<number_type>\#|GH-|PR-) # Hashtag or "GH-" or "PR-"
            (?P<number>\d*)             # followed by numbers
        )
    |                                   # Or
        (?:@?(?P<sha>[0-9a-f]{40}))     # at sign followed by 40 hexadecimal characters
    )
''', re.VERBOSE)
