import datetime
import time
from typing import Union

import discord

from plugins.base import BasePlugin


class VcParticipationTimeSlice:
    start_time: int
    end_time: int = -1

    def __init__(self, start_time: int):
        self.start_time = start_time

    def set_end_time(self, end_time: int):
        self.end_time = end_time


class VcParticipant:
    author_id: int
    time_slices: list[VcParticipationTimeSlice] = []

    def __init__(self, author_id: int):
        self.author_id = author_id
        self.time_slices = []


class VoiceAnnouncer(BasePlugin):
    vc_announce_channels: list[Union[discord.Thread, discord.TextChannel]] = []
    vc_participants: dict[int, dict[int, VcParticipant]] = {}
    voice_channels: list[discord.VoiceChannel] = []

    def on_ready(self):
        if self.is_ready():
            return
        if 'VC_ANNOUNCE_CHANNELS' in self.config:
            vc_announce_channels = self.config['VC_ANNOUNCE_CHANNELS'].split(',')
            for channel_id in vc_announce_channels:
                self.vc_announce_channels.append(self.client.get_channel(int(channel_id)))
        guild: discord.Guild = self.client.guilds[0]
        self.voice_channels = list(filter(lambda c: isinstance(c, discord.VoiceChannel), guild.channels))

    async def voice_status_update(self, member: discord.Member, before, after):
        current_epoch = int(time.time())
        if before.channel is None and after.channel is not None:
            channel_id = after.channel.id
            on_channel_text = f' on <#{channel_id}>' if len(self.voice_channels) > 1 else ''
            if channel_id not in self.vc_participants:
                self.vc_participants[channel_id] = dict()
            if member.id not in self.vc_participants[channel_id]:
                participant = VcParticipant(member.id)
                self.vc_participants[channel_id][member.id] = participant
            else:
                participant = self.vc_participants[channel_id][member.id]
            participant.time_slices.append(VcParticipationTimeSlice(current_epoch))
            if len(after.channel.members) == 1:
                for channel in self.vc_announce_channels:
                    await channel.send(
                        f'<@{member.id}> has started a VC' + on_channel_text,
                        allowed_mentions=discord.AllowedMentions(users=False)
                    )
        elif before.channel is not None and after.channel is None:
            channel_id = before.channel.id
            if channel_id not in self.vc_participants or len(self.vc_participants[channel_id]) == 0:
                return
            vc_participants = self.vc_participants[channel_id]
            vc_participants[member.id].time_slices[-1].set_end_time(current_epoch)
            on_channel_text = f' on <#{channel_id}>' if len(self.voice_channels) > 1 else ''
            if len(before.channel.members) == 0:
                msg_prefix = f'VC{on_channel_text} has ended :('
                if len(vc_participants) > 1:
                    participants = []
                    for member_id in vc_participants:
                        vc_participant = vc_participants[member_id]
                        participation_seconds = 0
                        for time_slice in vc_participant.time_slices:
                            participation_seconds += time_slice.end_time - time_slice.start_time
                        participation_time = str(datetime.timedelta(seconds=participation_seconds))
                        participants.append(f'* <@{member_id}> {participation_time}')
                    participants_list_txt = "\n".join(participants)
                    message = f'{msg_prefix}\nThanks to all the participants!\n{participants_list_txt}'
                else:
                    message = f'{msg_prefix}\nThat was a lonely one, sorry <@{member.id}>'
                self.vc_participants[channel_id] = dict()
                for channel in self.vc_announce_channels:
                    await channel.send(message, allowed_mentions=discord.AllowedMentions(users=False))
                return
