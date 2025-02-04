import os.path

import discord
from dotenv import dotenv_values

from plugins.activity_tracker.main import ActivityTracker
from plugins.anon_messenger.main import AnonMessenger
from plugins.banner_randomizer.main import BannerRandomizer
from plugins.comment_hearter.main import CommentHearter
from plugins.duckhunt.main import DuckHuntGame
from plugins.gifty_santa.main import GiftySanta
from plugins.hallucinater.main import Hallucinater
from plugins.icon_flipper.main import IconFlipper
from plugins.reaction_tracker.main import ReactionTracker
from plugins.repost_watcher.main import RepostWatcher
from plugins.smoothie_maker.main import SmoothieMaker
from plugins.time_assistant.main import TimeAssistant
from plugins.twitch_announcer.main import TwitchAnnouncer
from plugins.user_message_responder.main import UserMessageResponder
from plugins.user_silencer.main import UserSilencer
from plugins.voice_announcer.main import VoiceAnnouncer
from plugins.whos_that_monster.main import WhosThatMonster
from plugins.youtube_announcer.main import YoutubeAnnouncer

if not os.path.exists('.env'):
    raise Exception(".env is missing - see .env.example")

config = dotenv_values('.env')

if 'DISCORD_TOKEN' not in config:
    raise Exception("DISCORD_TOKEN is not configured")

TOKEN = config['DISCORD_TOKEN']

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True
intents.dm_messages = True
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
reaction_tracker = ReactionTracker(client, config)
whos_that_monster = WhosThatMonster(client, config)
anon_messenger = AnonMessenger(client, config)
gifty_santa = GiftySanta(client, config)
activity_tracker = ActivityTracker(client, config)
hallucinater = Hallucinater(client, config)


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
    reaction_tracker.on_ready()
    whos_that_monster.on_ready()


@client.event
async def on_message(message: discord.Message):
    if message.author.id == client.user.id:
        return
    if message.channel.type == discord.ChannelType.private \
            and client.guilds[0].get_member(message.author.id) is not None:
        await reaction_tracker.on_message(message)
        await anon_messenger.on_message(message)
        await gifty_santa.on_message(message)
        await whos_that_monster.on_message(message)
        return
    await gifty_santa.on_message(message)
    await smoothie_maker.on_message(message)
    await comment_hearter.on_message(message)
    await duckhunt_game.on_message(message)
    await user_silencer.on_message(message)
    await time_assistant.on_message(message)
    await repost_watcher.on_message(message)
    await user_message_responder.on_message(message)
    await banner_randomizer.on_message(message)
    await reaction_tracker.on_message(message)
    await whos_that_monster.on_message(message)
    await activity_tracker.on_message(message)
    await hallucinater.on_message(message)


@client.event
async def on_voice_state_update(member, before, after):
    await voice_announcer.voice_status_update(member, before, after)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    await reaction_tracker.track_reaction(payload)


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    await reaction_tracker.track_reaction(payload)


@client.event
async def on_presence_update(before, after):
    await activity_tracker.presence_update(before, after)


client.run(TOKEN)
