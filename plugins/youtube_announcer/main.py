import asyncio
import datetime
import time

import discord
from googleapiclient.discovery import build

from database.helper import GFDDatabaseHelper
from database.models import AnnouncedYoutubeVideo


class YoutubeAnnouncer:
    playlists_to_track = []
    client = None
    config = None
    youtube = None
    channel = None
    date_format = '%Y-%m-%dT%H:%M:%SZ%Z'
    videos_encountered = []

    def __init__(self, client, config):
        self.client = client
        self.config = config
        self.playlists_to_track = config['YT_PLAYLISTS_TO_TRACK'].split(',')

        for channel in self.client.guilds[0].channels:
            if channel.name == config['CHANNEL_FOR_YT_ANNOUNCEMENT']:
                self.channel = channel
                break

        if self.channel is None:
            return

        api_service_name = 'youtube'
        api_version = 'v3'
        dev_key = config['GOOGLE_API_KEY']
        self.youtube = build(api_service_name, api_version, developerKey=dev_key)
        asyncio.get_event_loop().create_task(self.check_playlists_for_new_videos())

    async def check_playlists_for_new_videos(self):
        while True:
            try:
                self.videos_encountered = self.videos_encountered[-100:]
                for playlist_id in self.playlists_to_track:
                    await self.check_playlist_for_new_videos(playlist_id)
            except Exception:
                pass
            await asyncio.sleep(60)

    async def check_playlist_for_new_videos(self, playlist_id):
        print(f'Checking playlist {playlist_id} for videos')
        request = self.youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            order='date'
        )
        response = request.execute()
        for video in response['items']:
            dateobj = datetime.datetime.strptime(video['snippet']['publishedAt'] + 'UTC', self.date_format)
            epoch_time = dateobj.timestamp()
            seconds_elapsed = time.time() - epoch_time
            if seconds_elapsed <= 1800 and video['id'] not in self.videos_encountered:
                print(f'Trying to post video {video["snippet"]["title"]}')
                self.videos_encountered.append(video['id'])
                await self.post_video_to_channel(video['id']['videoId'], video)

    async def post_video_to_channel(self, video_id, video):
        GFDDatabaseHelper.replenish_db()
        should_announce = AnnouncedYoutubeVideo.should_announce(video_id)
        GFDDatabaseHelper.release_db()
        if should_announce:
            print(f'Posting video {video["snippet"]["title"]}')
            thumb_quality = list(video['snippet']['thumbnails'].keys())[-1]
            embed = discord.Embed()
            embed.title = video['snippet']['title']
            embed.set_image(url=video['snippet']['thumbnails'][thumb_quality]['url'])
            embed.url = 'https://youtu.be/' + video_id
            await self.channel.send(embed=embed)
