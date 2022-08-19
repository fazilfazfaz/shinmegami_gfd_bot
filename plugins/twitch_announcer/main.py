import asyncio
import time

import discord
import requests


class TwitchAnnouncer:
    channels_to_track = []
    live_channels = set([])
    client = None
    config = None
    channel = None
    access_key = None
    access_key_expire_time = None

    def __init__(self, client, config):
        self.client = client
        self.config = config
        if 'TWITCH_CHANNELS_TO_TRACK' in config:
            self.channels_to_track = config['TWITCH_CHANNELS_TO_TRACK'].split(',')

        if 'CHANNEL_FOR_TWITCH_ANNOUNCEMENT' in config:
            for channel in self.client.guilds[0].channels:
                if str(channel.id) == config['CHANNEL_FOR_TWITCH_ANNOUNCEMENT']:
                    self.channel = channel
                    break

        if self.channel is None:
            return

        if 'TWITCH_CLIENT_ID' not in config or 'TWITCH_CLIENT_SECRET' not in config:
            return

        asyncio.get_event_loop().create_task(self.poll_twitch())

    def refresh_twitch_key(self):
        if self.access_key is None or self.access_key_expire_time <= time.time():
            print(f'Fetching twitch key')
            r = requests.post(url='https://id.twitch.tv/oauth2/token', data={
                'client_id': self.config['TWITCH_CLIENT_ID'],
                'client_secret': self.config['TWITCH_CLIENT_SECRET'],
                'grant_type': 'client_credentials'
            })
            assert r.status_code == 200
            jsondata = r.json()
            self.access_key = jsondata['access_token']
            self.access_key_expire_time = time.time() + jsondata['expires_in'] - 120

    async def get_channel_statuses(self):
        r = requests.get('https://api.twitch.tv/helix/streams', params={
            'user_login': self.channels_to_track,
        }, headers={
            'Client-Id': self.config['TWITCH_CLIENT_ID'],
            'Authorization': 'Bearer ' + self.access_key
        })
        assert r.status_code == 200
        jsondata = r.json()
        channels_now_offline = self.live_channels.copy()
        for stream in jsondata['data']:
            if stream['user_name'] in channels_now_offline:
                channels_now_offline.remove(stream['user_name'])
            else:
                await self.post_announcement_if_necessary(stream)

        for offline_channel in channels_now_offline:
            print(f'{offline_channel} is now offline')
            await self.channel.send(content=f'{offline_channel} is now offline on twitch :(')

        self.live_channels -= channels_now_offline

    async def post_announcement_if_necessary(self, stream):
        if stream['user_name'] in self.live_channels:
            return
        print(f'Posting twitch announcement for {stream["user_name"]}')
        self.live_channels.add(stream['user_name'])
        embed = discord.Embed()
        stream_url = 'https://twitch.tv/' + stream['user_name']
        embed.url = stream_url
        embed.title = f'{stream["user_name"]} is now live on twitch!'
        embed.set_image(url=stream['thumbnail_url'].replace('-{width}x{height}', ''))
        await self.channel.send(embed=embed)

    async def poll_twitch(self):
        while True:
            try:
                self.refresh_twitch_key()
                await self.get_channel_statuses()
                await asyncio.sleep(60)
            except Exception:
                pass
