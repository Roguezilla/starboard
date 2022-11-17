from typing import List

from .message import Application, Emoji, Member, User, test


class ReadyEvent:
    class __PartialGuild:
        def __init__(self, guild):
            self.id = guild['id']
            self.unavailable = guild['unavailable']

    def __init__(self, ready):
        self.v = ready['v']
        self.user = User(ready['user'])

        self.guilds: List[self.__PartialGuild] = []
        for guild in ready['guilds']:
                self.guilds.append(self.__PartialGuild(guild))

        self.session_id = ready['session_id']
        self.shard = test(ready, 'shard')
        self.application = Application(ready['application'])

class ReactionAddEvent:
    def __init__(self, event):
        self.user_id = event['user_id']
        self.message_id = event['message_id']
        self.author = Member(event['member']['user'], event['member'])
        self.emoji = Emoji(event['emoji'])
        self.channel_id = event['channel_id']
        self.guild_id = event['guild_id']