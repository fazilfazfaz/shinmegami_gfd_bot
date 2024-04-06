import os.path

import discord
from dotenv import dotenv_values

from plugins.banner_randomizer.main import BannerRandomizer
from plugins.comment_hearter.main import CommentHearter
from plugins.duckhunt.main import DuckHuntGame
from plugins.icon_flipper.main import IconFlipper
from plugins.repost_watcher.main import RepostWatcher
from plugins.smoothie_maker.main import SmoothieMaker
from plugins.time_assistant.main import TimeAssistant
from plugins.twitch_announcer.main import TwitchAnnouncer
from plugins.user_message_responder.main import UserMessageResponder
from plugins.user_silencer.main import UserSilencer
from plugins.voice_announcer.main import VoiceAnnouncer
from plugins.youtube_announcer.main import YoutubeAnnouncer

if not os.path.exists('.env'):
    raise Exception(".env is missing - see .env.example")

config = dotenv_values('.env')

if 'DISCORD_TOKEN' not in config:
    raise Exception("DISCORD_TOKEN is not configured")

TOKEN = config['DISCORD_TOKEN']

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)

comment_hearter = CommentHearter(client, config)
duckhunt_game = DuckHuntGame(client, config)
user_silencer = UserSilencer(client, config)
youtube_announcer = YoutubeAnnouncer(client, config)
twitch_announcer = TwitchAnnouncer(client, config)
smoothie_maker = SmoothieMaker(client, config)
time_assistant = TimeAssistant(client, config)
repost_watcher = RepostWatcher(client, config)
user_message_responder = UserMessageResponder(client, config)
voice_announcer = VoiceAnnouncer(client, config)
banner_randomizer = BannerRandomizer(client, config)
icon_flipper = IconFlipper(client, config)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    comment_hearter.on_ready()
    duckhunt_game.on_ready()
    user_silencer.on_ready()
    youtube_announcer.on_ready()
    twitch_announcer.on_ready()
    user_message_responder.on_ready()
    voice_announcer.on_ready()
    banner_randomizer.on_ready()
    icon_flipper.on_ready()


@client.event
async def on_message(message):
    if message.author.id == int(config['BOT_USER_ID']):
        return
    await smoothie_maker.on_message(message)
    await comment_hearter.on_message(message)
    await duckhunt_game.on_message(message)
    await user_silencer.on_message(message)
    await time_assistant.on_message(message)
    await repost_watcher.on_message(message)
    await user_message_responder.on_message(message)
    await banner_randomizer.on_message(message)


@client.event
async def on_voice_state_update(member, before, after):
    await voice_announcer.voice_status_update(member, before, after)


client.run(TOKEN)
