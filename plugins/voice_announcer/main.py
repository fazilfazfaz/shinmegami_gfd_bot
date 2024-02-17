from typing import Union

import discord

from plugins.base import BasePlugin


class VoiceAnnouncer(BasePlugin):
    vc_announce_channels: list[Union[discord.Thread, discord.TextChannel]] = []

    def on_ready(self):
        if self.is_ready():
            return
        if 'VC_ANNOUNCE_CHANNELS' in self.config:
            vc_announce_channels = self.config['VC_ANNOUNCE_CHANNELS'].split(',')
            for channel_id in vc_announce_channels:
                self.vc_announce_channels.append(self.client.get_channel(int(channel_id)))

    async def voice_status_update(self, member, before, after):
        if before.channel is None and after.channel is not None:
            if len(after.channel.members) == 1:
                for channel in self.vc_announce_channels:
                    await channel.send(f'{member.display_name} has started a VC')
        elif before.channel is not None and after.channel is None:
            if len(before.channel.members) == 0:
                for channel in self.vc_announce_channels:
                    await channel.send(f'VC has ended :(')
