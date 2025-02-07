import re

import discord

mention_no_one = discord.AllowedMentions(users=False, everyone=False, roles=False)


def escape_discord_identifiers(message):
    return re.sub(r'(<(@!?|#|@&|a?:\w+:)[0-9]+>|<t:[0-9]+(:[a-zA-Z]+)?>)', lambda match: "\\" + match.group(1), message)
