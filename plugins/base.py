import discord


class BasePlugin:
    started = False
    client = None
    config = None

    def __init__(self, client, config):
        self.client: discord.Client = client
        self.config = config

    def is_ready(self):
        if self.started:
            return self.started
        self.started = True
        return False
