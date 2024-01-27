import json
import os
from enum import Enum
from typing import Optional

import discord
import jsonschema

from plugins.base import BasePlugin


class ResponseConditionType(str, Enum):
    HAS_GIF = 'HAS_GIF'
    HAS_TEXT = 'HAS_TEXT'
    NOT_IN_CHANNEL = 'NOT_IN_CHANNEL'


class ResponseCondition:
    def __init__(self, condition_type: ResponseConditionType, value: Optional[str]):
        self.value = value
        self.condition_type = condition_type


class Response:
    def __init__(self, user_ids: list[int], conditions: list[ResponseCondition], message: str):
        self.user_ids = user_ids
        self.conditions = conditions
        self.message = message


class UserMessageResponder(BasePlugin):
    responses: list[Response] = []

    def on_ready(self):
        if self.is_ready():
            return
        dir_path = os.path.realpath(os.path.dirname(__file__))
        with open(os.path.join(dir_path, 'responses.json'), 'r') as f:
            response_json = json.load(f)
        with open(os.path.join(dir_path, 'responses.schema.json'), 'r') as f:
            schema = json.load(f)
        jsonschema.validate(response_json, schema)
        for response in response_json:
            conditions = []
            if 'conditions' in response:
                for condition in response['conditions']:
                    condition_type: ResponseConditionType = ResponseConditionType[condition['type']]
                    condition_value = condition['value'] if 'value' in condition else None
                    conditions.append(ResponseCondition(condition_type, condition_value))
            user_ids = response['user_ids'] if 'user_ids' in response else []
            self.responses.append(Response(user_ids, conditions, response['message']))

    async def on_message(self, message: discord.Message):
        if len(self.responses) < 1:
            return
        for _ in self.responses:
            if len(_.user_ids) > 0:
                if message.author.id not in _.user_ids:
                    continue
            if not self.response_applicable(_, message):
                continue
            await message.reply(_.message, mention_author=False)

    @staticmethod
    def response_applicable(response: Response, message: discord.Message) -> bool:
        if len(response.conditions) > 0:
            for condition in response.conditions:
                if condition.condition_type == ResponseConditionType.HAS_GIF:
                    if 'https://tenor.com' not in message.content:
                        return False
                elif condition.condition_type == ResponseConditionType.HAS_TEXT:
                    if condition.value.lower() not in message.content.lower():
                        return False
                elif condition.condition_type == ResponseConditionType.NOT_IN_CHANNEL:
                    channels = condition.value.split(',')
                    if str(message.channel.id) in channels:
                        return False
        return True
