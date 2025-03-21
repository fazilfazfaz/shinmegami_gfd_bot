import datetime
import io
import json
import os
import random
import time
from io import BytesIO
from typing import Union

import discord
import jsonschema
from PIL import Image

from logger import logger
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
    time_slices: list[VcParticipationTimeSlice]

    def __init__(self, author_id: int):
        self.author_id = author_id
        self.time_slices = []


class VcAnnounceImage:
    filename: str
    avatar_resize_to: int
    avatar_position: tuple[int, int]

    def __init__(self, filename: str, avatar_resize_to: int, avatar_position: tuple[int, int]):
        self.filename = filename
        self.avatar_resize_to = avatar_resize_to
        self.avatar_position = avatar_position


class VoiceAnnouncer(BasePlugin):
    vc_announce_channels: list[Union[discord.Thread, discord.TextChannel]]
    vc_participants: dict[int, dict[int, VcParticipant]]
    voice_channels: list[discord.VoiceChannel]
    announce_images: list[VcAnnounceImage]

    def __init__(self, client, config):
        super().__init__(client, config)
        self.vc_announce_channels = []
        self.vc_participants = {}
        self.voice_channels = []
        self.announce_images = []
        self.load_announce_images()

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
                    announce_image_result = await self.get_announce_image(member)
                    if announce_image_result is not None:
                        image, image_format = announce_image_result
                        if image:
                            file = discord.File(image, filename=f"vc_announce_image.{image_format}")
                            await channel.send(
                                f'<@{member.id}> has started a VC' + on_channel_text,
                                allowed_mentions=discord.AllowedMentions(users=False),
                                file=file,
                            )
                    else:
                        await channel.send(
                            f'<@{member.id}> has started a VC' + on_channel_text,
                            allowed_mentions=discord.AllowedMentions(users=False),
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

    def load_announce_images(self):
        resources_dir = os.path.join(os.path.realpath(os.path.dirname(__file__)), '..', '..', 'resources')
        images_path = os.path.join(resources_dir, 'vc_announce_images', 'images.json')
        if not os.path.exists(images_path):
            return
        with open(os.path.join(resources_dir, 'schemas', 'vc_announce_images.schema.json'), 'r') as f:
            schema = json.load(f)
        with open(images_path, 'r') as f:
            images = json.load(f)
        jsonschema.validate(images, schema)
        for image in images:
            filename: str = image['filename']
            self.announce_images.append(VcAnnounceImage(
                filename=os.path.join(resources_dir, 'vc_announce_images', filename),
                avatar_resize_to=image['avatar_resize_to'],
                avatar_position=(image['avatar_position_x'], image['avatar_position_y'])
            ))

    async def get_announce_image(self, member: discord.Member) -> tuple[BytesIO, str | None] | None:
        if len(self.announce_images) == 0:
            return None
        try:
            announce_image = random.choice(self.announce_images)
            avatar_image_bytes = io.BytesIO()
            await member.avatar.save(avatar_image_bytes)
            avatar_image_bytes.seek(0)
            avatar_image = Image.open(avatar_image_bytes).convert("RGBA")
            avatar_image = avatar_image.resize((announce_image.avatar_resize_to, announce_image.avatar_resize_to))
            announce_image_img = Image.open(announce_image.filename)
            announce_image_img.paste(avatar_image, announce_image.avatar_position, avatar_image)
            announce_image_bytes = io.BytesIO()
            announce_image_img.save(announce_image_bytes, announce_image_img.format)
            announce_image_bytes.seek(0)
            return announce_image_bytes, announce_image_img.format
        except Exception as e:
            logger.error('Failed to get announce image' + str(e))
            return None
