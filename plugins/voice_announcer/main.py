import datetime
import time
from typing import Union

import discord

from plugins.base import BasePlugin


class VcParticipant:
    author_id: int
    start_time: int
    end_time: int

    def __init__(self, author_id: int, start_time: int):
        self.author_id = author_id
        self.start_time = start_time

    def set_end_time(self, end_time: int):
        self.end_time = end_time


class VoiceAnnouncer(BasePlugin):
    vc_announce_channels: list[Union[discord.Thread, discord.TextChannel]] = []
    vc_participants: dict[int, dict[int, VcParticipant]] = {}

    def on_ready(self):
        if self.is_ready():
            return
        if 'VC_ANNOUNCE_CHANNELS' in self.config:
            vc_announce_channels = self.config['VC_ANNOUNCE_CHANNELS'].split(',')
            for channel_id in vc_announce_channels:
                self.vc_announce_channels.append(self.client.get_channel(int(channel_id)))

    async def voice_status_update(self, member: discord.Member, before, after):
        if before.channel is None and after.channel is not None:
            if len(after.channel.members) == 1:
                self.vc_participants[after.channel.id] = dict()
                for channel in self.vc_announce_channels:
                    await channel.send(f'<@{member.id}> has started a VC', mention_author=False)
            participant = VcParticipant(member.id, int(time.time()))
            self.vc_participants[after.channel.id][member.id] = participant
        elif before.channel is not None and after.channel is None:
            vc_participants = self.vc_participants[before.channel.id]
            vc_participants[member.id].set_end_time(int(time.time()))
            if len(before.channel.members) == 0:
                participants = []
                for member_id in vc_participants:
                    participation_seconds = vc_participants[member_id].end_time - vc_participants[member_id].start_time
                    participation_time = str(datetime.timedelta(seconds=participation_seconds))
                    participants.append(f'* <@{member_id}> {participation_time}')
                participants_list_txt = "\n".join(participants)
                message = f'VC has ended :(\nThanks to all the participants!\n{participants_list_txt}'
                del self.vc_participants[before.channel.id]
                for channel in self.vc_announce_channels:
                    await channel.send(message, mention_author=False)
                return
