import discord
from dotenv import dotenv_values

from database.helper import GFDDatabaseHelper
from plugins.comment_hearter.main import CommentHearter
from plugins.duckhunt.main import DuckHuntGame
from plugins.smoothie_maker.main import SmoothieMaker
from plugins.twitch_announcer.main import TwitchAnnouncer
from plugins.user_silencer.main import UserSilencer
from plugins.youtube_announcer.main import YoutubeAnnouncer

config = dotenv_values('.env')

TOKEN = config['DISCORD_TOKEN']

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    GFDDatabaseHelper()
    comment_hearter = CommentHearter(client, config)
    duckhunt_game = DuckHuntGame(client, config)
    user_silencer = UserSilencer(client, config)
    YoutubeAnnouncer(client, config)
    TwitchAnnouncer(client, config)
    smoothie_maker = SmoothieMaker(client, config)

    @client.event
    async def on_message(message):
        await smoothie_maker.on_message(message)
        await comment_hearter.on_message(message)
        await duckhunt_game.on_message(message)
        await user_silencer.on_message(message)


client.run(TOKEN)
