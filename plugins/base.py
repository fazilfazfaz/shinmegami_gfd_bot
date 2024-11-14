import discord


class BasePlugin:

    def __init__(self, client, config):
        self.started = False
        self.client: discord.Client = client
        self.config = config

    def is_ready(self):
        if self.started:
            return self.started
        self.started = True
        return False
