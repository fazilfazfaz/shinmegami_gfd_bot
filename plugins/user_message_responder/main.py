import json
import os
from enum import Enum
from typing import Optional

import discord
import jsonschema

from plugins.base import BasePlugin


class ResponseConditionType(Enum):
    HAS_GIF = 'HAS_GIF'
    EXACT_TEXT = 'EXACT_TEXT'
    HAS_TEXT = 'HAS_TEXT'
    NOT_IN_CHANNEL = 'NOT_IN_CHANNEL'


class ResponseCondition:
    def __init__(self, condition_type: ResponseConditionType, value: Optional[str]):
        self.value = value
        self.condition_type = condition_type


class MessageProcessorType(Enum):
    COUNTDOWN = 'COUNTDOWN'


class MessageProcessor:
    def __init__(self, message_processor_type: MessageProcessorType, message_processor_args: dict):
        self.message_processor_type = message_processor_type
        self.message_processor_args = message_processor_args


class Response:
    def __init__(
            self,
            user_ids: list[int],
            conditions: list[ResponseCondition],
            message: str,
            message_processor: Optional[MessageProcessor] = None,
    ):
        self.user_ids = user_ids
        self.conditions = conditions
        self.message = message
        self.message_processor = message_processor


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
                    condition_type = ResponseConditionType[condition['type']]
                    condition_value = condition['value'] if 'value' in condition else None
                    conditions.append(ResponseCondition(condition_type, condition_value))
            message_processor = None
            if 'messageProcessor' in response:
                message_processor_type = MessageProcessorType[response['messageProcessor']]
                message_processor_args = response.get('messageProcessorArgs', None)
                message_processor = MessageProcessor(message_processor_type, message_processor_args)
            user_ids = response['user_ids'] if 'user_ids' in response else []
            r = Response(user_ids, conditions, response['message'], message_processor)
            self.responses.append(r)

    async def on_message(self, message: discord.Message):
        if len(self.responses) < 1:
            return
        for _ in self.responses:
            if len(_.user_ids) > 0:
                if message.author.id not in _.user_ids:
                    continue
            if not self.response_applicable(_, message):
                continue
            resp_message = _.message
            if _.message_processor is not None:
                resp_message = self.run_message_processor(_.message_processor, resp_message)
            await message.reply(resp_message, mention_author=False)

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
                elif condition.condition_type == ResponseConditionType.EXACT_TEXT:
                    if condition.value.lower() != message.content.lower():
                        return False
                elif condition.condition_type == ResponseConditionType.NOT_IN_CHANNEL:
                    channels = condition.value.split(',')
                    if str(message.channel.id) in channels:
                        return False
        return True

    @staticmethod
    def run_message_processor(message_processor, resp_message) -> str:
        if message_processor.message_processor_type == MessageProcessorType.COUNTDOWN:
            countdown_to = message_processor.message_processor_args['countdownTo']
            seconds_until = countdown_to - int(discord.utils.utcnow().timestamp())
            if seconds_until < 0:
                return 'This countdown was already completed!'
            days, hours, minutes, seconds = (
                seconds_until // 86400,
                (seconds_until % 86400) // 3600,
                (seconds_until % 3600) // 60,
                seconds_until % 60,
            )
            units = {
                'D': (days, 'Day' if days == 1 else 'Days'),
                'H': (hours, 'Hour' if hours == 1 else 'Hours'),
                'M': (minutes, 'Min' if minutes == 1 else 'Mins'),
                'S': (seconds, 'Sec' if seconds == 1 else 'Secs'),
            }
            for key, (value, text) in units.items():
                resp_message = resp_message.replace(f'{{{key}}}', str(value)).replace(f'{{{key}T}}', text)
            return resp_message
        return resp_message
