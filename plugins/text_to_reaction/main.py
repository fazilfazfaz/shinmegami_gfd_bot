from typing import Optional, List

import discord

from plugins.base import BasePlugin


class TextToReaction(BasePlugin):
    emoji_replacements = {
        "II": [0x23F8],  # ⏸️ :pause_button:
        "ID": [0x1F194],  # 🆔 :id:
        "OFF": [0x1F4F4],  # 📴 :mobile_phone_off:
        "VS": [0x1F19A],  # 🆚 :vs:
        "AB": [0x1F18E],  # 🆎 :ab:
        "CL": [0x1F191],  # 🆑 :cl:
        "SOS": [0x1F198],  # 🆘 :sos:
        "ATM": [0x1F3E7],  # 🏧 :atm:
        "WC": [0x1F6BE],  # 🚾 :wc:
        "ABC": [0x1F524],  # 🔤 :abc:
        "NG": [0x1F196],  # 🆖 :ng:
        "OK": [0x1F197],  # 🆗 :ok:
        "UP": [0x1F199],  # 🆙 :up:
        "COOL": [0x1F192],  # 🆒 :cool:
        "NEW": [0x1F195],  # 🆕 :new:
        "FREE": [0x1F193],  # 🆓 :free:
        "END": [0x1F51A],  # 🔚 :end:
        "BACK": [0x1F519],  # 🔙 :back:
        "ON": [0x1F51B],  # 🔛 :on:
        "TOP": [0x1F51D],  # 🔝 :top:
        "SOON": [0x1F51C],  # 🔜 :soon:
        "ZZZ": [0x1F4A4],  # 💤 :zzz:
        "A": [0x1F1E6, 0x1F170, 0x1F53A],  # 🇦 🅰️🔺
        "B": [0x1F1E7, 0x1F171],  # 🇧 🅱️
        "C": [0x1F1E8, 0x000A9],  # 🇨 ©️
        "D": [0x1F1E9, 0x25B6],  # 🇩 ▶️
        "E": [0x1F1EA],  # 🇪
        "F": [0x1F1EB],  # 🇫
        "G": [0x1F1EC],  # 🇬
        "H": [0x1F1ED, 0x0023],  # 🇭 #
        "I": [0x1F1EE, 0x2139],  # 🇮 ℹ️
        "J": [0x1F1EF],  # 🇯
        "K": [0x1F1F0],  # 🇰
        "L": [0x1F1F1, 0x1F552],  # 🇱 🕒
        "M": [0x1F1F2, 0x264F, 0x264D],  # 🇲 ♏ ♍
        "N": [0x1F1F3, 0x2651],  # 🇳 ♑
        "O": [0x1F1F4, 0x1F17E, 0x2B55, 0x1F6DF, 0x23FA],  # 🇴 🅾️ ⭕ 🛟 ⏺️
        "P": [0x1F1F5, 0x1F17F],  # 🇵 🅿️
        "Q": [0x1F1F6],  # 🇶
        "R": [0x1F1F7, 0x000AE],  # 🇷 ®️
        "S": [0x1F1F8, 0x1F4B2],  # 🇸💲
        "T": [0x1F1F9, 0x271D],  # 🇹 ✝️
        "U": [0x1F1FA, 0x26CE],  # 🇺 ⛎
        "V": [0x1F1FB, 0x2648, 0x2611, 0x2705, 0x2714],  # 🇻 ♈ ☑️ ✅ ✔️
        "W": [0x1F1FC, 0x3030],  # 🇼 〰️
        "X": [0x1F1FD, 0x274E, 0x2716, 0x274C],  # 🇽 ❎ ❌ ❌
        "Y": [0x1F1FE],  # 🇾
        "Z": [0x1F1FF],  # 🇿
        "10": [0x1F51F],  # 🔟
        "100": [0x1F4AF],  # 💯
        "1": [0x0031, 0x1F947],  # 1 🥇
        "2": [0x0032, 0x1F948],  # 2 🥈
        "3": [0x0033, 0x1F949],  # 3 🥉
        "4": [0x0034],  # 4
        "5": [0x0035],  # 5
        "6": [0x0036],  # 6
        "7": [0x0037],  # 7
        "8": [0x0038, 0x1F3B1],  # 8 🎱
        "9": [0x0039],  # 9
        "0": [0x0030],  # 0
        "!!": [0x203C],  # ‼️
        "!?": [0x2049],  # ⁉️
        "!": [0x2757, 0x2755],  # ❗ ❕
        "?": [0x2753, 0x2754],  # ❓ ❔
    }

    sorted_emoji_replacements = sorted(emoji_replacements.keys(), key=len, reverse=True)

    def __init__(self, client: discord.Client, config: dict):
        super().__init__(client, config)

    @staticmethod
    async def on_message(message: discord.Message):
        msg_lower = message.content.lower()
        if not msg_lower.startswith('.react-text '):
            return
        if message.reference is None or not isinstance(message.reference, discord.MessageReference):
            await message.add_reaction('🚫')
            return
        replied_to_message = await message.channel.fetch_message(message.reference.message_id)
        text_to_react = msg_lower[12:]
        if len(text_to_react) < 1:
            await message.add_reaction('🚫')
            return
        emojis_to_react = TextToReaction.text_to_emojis(text_to_react)
        if emojis_to_react is None:
            await message.add_reaction('🚫')
            return
        for emoji in emojis_to_react:
            await replied_to_message.add_reaction(emoji)

    @staticmethod
    def text_to_emojis(inp_original: str) -> Optional[List[str]]:
        """
        Converts a string into a sequence of emoji substitutes using emojiDict.
        """
        # Normalize input
        inp = inp_original.upper().replace(' ', '')

        # Pre-sort keys by length (longest first to avoid partial matches overriding longer ones)
        key_indices = {}

        def get_next_match(start: int) -> tuple[Optional[int], int]:
            """Returns the Unicode for the next character and the length of the match."""
            for key in TextToReaction.sorted_emoji_replacements:
                if inp.startswith(key, start):
                    if key not in key_indices:
                        key_indices[key] = 0
                    else:
                        if key_indices[key] + 1 >= len(TextToReaction.emoji_replacements[key]):
                            continue
                        key_indices[key] += 1
                    return TextToReaction.emoji_replacements[key][key_indices[key]], len(
                        key)  # Take the first substitute
            return None, 0

        result = []
        i = 0

        # Main loop for processing the string
        while i < len(inp):
            substitute, add_len = get_next_match(i)
            if substitute is None:  # No valid substitute found
                return None
            result.append(chr(substitute))  # Convert the unicode int to a char
            i += add_len

        return result
