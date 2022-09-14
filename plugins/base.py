class BasePlugin:
    started = False

    def __init__(self, client, config):
        self.client = client
        self.config = config

    def is_ready(self):
        if self.started:
            return self.started
        self.started = True
        return False
