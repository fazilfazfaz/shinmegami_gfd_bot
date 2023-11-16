import re

from database.helper import gfd_links_database_helper
from database.models import PostedLink
from plugins.base import BasePlugin


class RepostWatcher(BasePlugin):
    basic_url_regex_pattern = re.compile(r'https?://[^\s]{1,2048}', re.DOTALL)

    async def on_message(self, message):
        if message.content == '.toplinks':
            await self.post_top_links(message)
            return
        reacted = False
        for link in re.finditer(self.basic_url_regex_pattern, message.content):
            posted_link = await self.process_link(link.group(0))
            if reacted is False and posted_link.hits > 1:
                reacted = True
                await message.add_reaction('♻')

    @staticmethod
    async def process_link(link) -> PostedLink:
        gfd_links_database_helper.replenish_db()
        posted_link: PostedLink
        posted_link, create = PostedLink.get_or_create(link=link)
        posted_link.increment_hits()
        posted_link.save()
        gfd_links_database_helper.release_db()
        return posted_link

    @staticmethod
    async def post_top_links(message):
        gfd_links_database_helper.replenish_db()
        num_links = 10
        posted_links: list[PostedLink] = PostedLink.get_top_links(num_links)
        gfd_links_database_helper.release_db()
        if len(posted_links) < 1:
            await message.reply('No links recorded yet')
            return
        message_parts = [
            f'These are the top {num_links} links posted:',
        ]
        for posted_link in posted_links:
            times = 'times' if posted_link.hits > 1 else 'time'
            message_parts.append(f'<{posted_link.link}> ({posted_link.hits} {times})')
        await message.reply("\n".join(message_parts))
