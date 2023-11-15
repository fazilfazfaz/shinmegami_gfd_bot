import re

from database.helper import gfd_links_database_helper
from database.models import PostedLink
from plugins.base import BasePlugin


class RepostWatcher(BasePlugin):
    basic_url_regex_pattern = re.compile(r'https?://[^ ]{0,2048}')
    number_emoji_map = {
        1: '1️⃣',
        2: '2️⃣',
        3: '3️⃣',
        4: '4️⃣',
        5: '5️⃣',
        6: '6️⃣',
        7: '7️⃣',
        8: '8️⃣',
        9: '9️⃣',
    }

    async def on_message(self, message):
        reacted = False
        for link in re.finditer(self.basic_url_regex_pattern, message.clean_content):
            posted_link = await self.process_link(link)
            if reacted is False and posted_link.hits > 1:
                reacted = True
                for digit in self.emoji_numbers_for_hits(int(posted_link.hits) - 1):
                    await message.add_reaction(digit)
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

    def emoji_numbers_for_hits(self, hits):
        if hits < 10:
            yield self.number_emoji_map[hits]
            return
        yield from self.emoji_numbers_for_hits(hits // 10)
        yield self.number_emoji_map[hits % 10]
