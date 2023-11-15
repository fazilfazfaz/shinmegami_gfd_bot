from database.helper import gfd_links_database_helper
from database.models import PostedLink
from plugins.base import BasePlugin


class RepostWatcher(BasePlugin):
    number_emoji_map = {
        0: '0️⃣',
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
        react_count = 0
        for embed in message.embeds:
            if embed.url != '':
                posted_link = await self.process_link(embed.url)
                if posted_link.hits > 1:
                    if react_count == 0:
                        react_count = int(posted_link.hits) - 1
                    else:
                        react_count = min(react_count, int(posted_link.hits) - 1)
        if react_count > 0:
            for digit in self.emoji_numbers_for_hits(react_count):
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
