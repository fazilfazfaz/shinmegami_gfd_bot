import re

import discord

mention_no_one = discord.AllowedMentions(users=False, everyone=False, roles=False, replied_user=False)


def escape_discord_identifiers(message):
    return re.sub(r'(<(@!?|#|@&|a?:\w+:)[0-9]+>|<t:[0-9]+(:[a-zA-Z]+)?>)', lambda match: "\\" + match.group(1), message)


def get_image_attachment_count(message: discord.Message):
    return sum(1 for attachment in message.attachments if
               attachment.content_type and attachment.content_type.startswith('image/'))
