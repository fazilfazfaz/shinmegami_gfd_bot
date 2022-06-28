import discord
from dotenv import dotenv_values

from database.helper import GFDDatabaseHelper
from games.comment_hearter.main import CommentHearter
from games.duckhunt.main import DuckHuntGame
from games.user_silencer.main import UserSilencer

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
    clip_silencer = UserSilencer(client, config)

    @client.event
    async def on_message(message):
        await comment_hearter.on_message(message)
        await duckhunt_game.on_message(message)
        await clip_silencer.on_message(message)


client.run(TOKEN)
