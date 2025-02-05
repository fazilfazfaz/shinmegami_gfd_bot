import asyncio
import datetime
import time

from googleapiclient.discovery import build

from database.helper import gfd_database_helper
from database.models import AnnouncedYoutubeVideo
from logger import logger
from plugins.base import BasePlugin


class YoutubeAnnouncer(BasePlugin):
    playlists_to_track = []
    youtube = None
    channel = None
    date_format = '%Y-%m-%dT%H:%M:%S%z'
    videos_encountered = []

    def on_ready(self):
        if self.is_ready():
            return
        if 'YT_PLAYLISTS_TO_TRACK' in self.config:
            self.playlists_to_track = self.config['YT_PLAYLISTS_TO_TRACK'].split(',')

        if 'CHANNEL_FOR_YT_ANNOUNCEMENT' in self.config:
            for channel in self.client.guilds[0].channels:
                if str(channel.id) == self.config['CHANNEL_FOR_YT_ANNOUNCEMENT']:
                    self.channel = channel
                    break

        if self.channel is None or 'GOOGLE_API_KEY' not in self.config:
            return

        api_service_name = 'youtube'
        api_version = 'v3'
        dev_key = self.config['GOOGLE_API_KEY']
        self.youtube = build(api_service_name, api_version, developerKey=dev_key)
        asyncio.get_event_loop().create_task(self.check_playlists_for_new_videos())

    async def check_playlists_for_new_videos(self):
        while True:
            try:
                self.videos_encountered = self.videos_encountered[-100:]
                for playlist_id in self.playlists_to_track:
                    await self.check_playlist_for_new_videos(playlist_id)
            except Exception as e:
                logger.error(f'Failed to fetch yt videos due to error: {str(e)}')
            await asyncio.sleep(180)

    async def check_playlist_for_new_videos(self, playlist_id):
        logger.info(f'Checking playlist {playlist_id} for videos')
        request = self.youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
        )
        response = request.execute()
        for video in response['items']:
            dateobj = datetime.datetime.strptime(video['snippet']['publishedAt'], self.date_format)
            epoch_time = dateobj.timestamp()
            seconds_elapsed = time.time() - epoch_time
            video_id = video['snippet']['resourceId']['videoId']
            if seconds_elapsed <= 1800 and video_id not in self.videos_encountered:
                logger.debug(f'Trying to post video {video["snippet"]["title"]}')
                self.videos_encountered.append(video_id)
                await self.post_video_to_channel(video_id, video)

    async def post_video_to_channel(self, video_id, video):
        gfd_database_helper.replenish_db()
        should_announce = AnnouncedYoutubeVideo.should_announce(video_id)
        gfd_database_helper.release_db()
        if should_announce:
            logger.debug(f'Posting video {video["snippet"]["title"]}')
            # thumb_quality = list(video['snippet']['thumbnails'].keys())[-1]
            # embed = discord.Embed()
            # embed.title = video['snippet']['title']
            # embed.set_image(url=video['snippet']['thumbnails'][thumb_quality]['url'])
            # embed.url = 'https://youtu.be/' + video_id
            await self.channel.send(content='https://youtu.be/' + video_id)
