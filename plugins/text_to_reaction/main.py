from typing import Optional, List

import discord

from plugins.base import BasePlugin


class TextToReaction(BasePlugin):
    emoji_replacements = {
        "II": ["⏸️"],
        "ID": ["🆔"],
        "OFF": ["📴"],
        "VS": ["🆚"],
        "AB": ["🆎"],
        "CL": ["🆑"],
        "SOS": ["🆘"],
        "ATM": ["🏧"],
        "WC": ["🚾"],
        "ABC": ["🔤"],
        "NG": ["🆖"],
        "OK": ["🆗"],
        "UP": ["🆙"],
        "COOL": ["🆒"],
        "NEW": ["🆕"],
        "FREE": ["🆓"],
        "END": ["🔚"],
        "BACK": ["🔙"],
        "ON": ["🔛"],
        "TOP": ["🔝"],
        "SOON": ["🔜"],
        "ZZZ": ["💤"],
        "A": ["🇦", "🅰️", "🔺"],
        "B": ["🇧", "🅱️"],
        "C": ["🇨", "©️"],
        "D": ["🇩", "▶️"],
        "E": ["🇪"],
        "F": ["🇫"],
        "G": ["🇬"],
        "H": ["🇭", "#️⃣"],
        "I": ["🇮", "ℹ️"],
        "J": ["🇯"],
        "K": ["🇰"],
        "L": ["🇱", "🕒"],
        "M": ["🇲", "♏", "♍"],
        "N": ["🇳", "♑"],
        "O": ["🇴", "🅾️", "⭕", "🛟", "⏺️"],
        "P": ["🇵", "🅿️"],
        "Q": ["🇶"],
        "R": ["🇷", "®️"],
        "S": ["🇸", "💲"],
        "T": ["🇹", "✝️"],
        "U": ["🇺", "⛎"],
        "V": ["🇻", "♈", "☑️", "✅", "✔️"],
        "W": ["🇼", "〰️"],
        "X": ["🇽", "❎", "❌", "❌"],
        "Y": ["🇾"],
        "Z": ["🇿"],
        "10": ["🔟"],
        "100": ["💯"],
        "1": ["1️⃣", "🥇"],
        "2": ["2️⃣", "🥈"],
        "3": ["3️⃣", "🥉"],
        "4": ["4️⃣"],
        "5": ["5️⃣"],
        "6": ["6️⃣"],
        "7": ["7️⃣"],
        "8": ["8️⃣", "🎱"],
        "9": ["9️⃣"],
        "0": ["0️⃣"],
        "!!": ["‼️"],
        "!?": ["⁉️"],
        "!": ["❗", "❕"],
        "?": ["❓", "❔"],
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
        existing_reactions = [reaction.emoji for reaction in replied_to_message.reactions]
        if any(emoji in existing_reactions for emoji in emojis_to_react):
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

        def get_next_match(start: int) -> tuple[Optional[str], int]:
            """Returns the Unicode for the next character and the length of the match."""
            for key in TextToReaction.sorted_emoji_replacements:
                if inp.startswith(key, start):
                    # ensure emojis are not reused
                    if key not in key_indices:
                        key_indices[key] = 0
                    else:
                        if key_indices[key] + 1 >= len(TextToReaction.emoji_replacements[key]):
                            continue
                        key_indices[key] += 1
                    emoji = TextToReaction.emoji_replacements[key][key_indices[key]]
                    return emoji, len(key)
            return None, 0

        result = []
        i = 0

        # Main loop for processing the string
        while i < len(inp):
            substitute, add_len = get_next_match(i)
            if substitute is None:  # No valid substitute found
                return None
            result.append(substitute)  # Convert the unicode int to a char
            i += add_len

        return result
