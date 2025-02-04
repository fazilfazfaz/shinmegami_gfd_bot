import asyncio
import re

import discord
import google.generativeai as genai

from plugins.base import BasePlugin


class Hallucinater(BasePlugin):

    def __init__(self, client, config):
        super().__init__(client, config)
        genai.configure(api_key=config.get('GEMINI_KEY'))
        self.rate_limiter = {}

    async def on_message(self, message: discord.Message):
        user_id = message.author.id
        current_time = asyncio.get_running_loop().time()
        if user_id in self.rate_limiter and current_time - self.rate_limiter[user_id] < 5:
            await message.reply("Slow down!")
            return
        self.rate_limiter[user_id] = current_time
        if not message.mention_everyone and self.client.user in message.mentions:
            user_prompt = message.content.replace(f'<@{self.client.user.id}>', '').strip()
            await self.respond_to_prompt(message, user_prompt)
            return
        if message.content.lower().startswith('herm,'):
            user_prompt = re.sub(r'^herm, *', '', message.content, flags=re.IGNORECASE).strip()
            await self.respond_to_prompt(message, user_prompt)

    @staticmethod
    async def respond_to_prompt(message, user_prompt):
        if user_prompt == '':
            await message.reply('I got nothing to say to that!')
            return
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        prompt = ('Respond to the prompt in the next line pretending to be a bot cat who is in to gaming.'
                  'Keep responses short and to the point.\n') + user_prompt
        response = await model.generate_content_async(prompt)
        await message.reply(response.text)
