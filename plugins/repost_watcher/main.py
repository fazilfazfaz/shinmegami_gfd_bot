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
        if message.content == '.toplinks':
            await self.post_top_links(message)
            return
        reacted = False
        for embed in message.embeds:
            if embed.url != '':
                posted_link = await self.process_link(embed.url)
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

    def emoji_numbers_for_hits(self, hits):
        if hits < 10:
            yield self.number_emoji_map[hits]
            return
        yield from self.emoji_numbers_for_hits(hits // 10)
        yield self.number_emoji_map[hits % 10]

    async def post_top_links(self, message):
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
