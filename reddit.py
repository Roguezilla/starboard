import re

import discord
import dataset
import requests
from discord.ext import commands


class Reddit(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.reddit = True
        self.db = db

    @staticmethod
    def return_reddit(url):
        try:
            # Form an API URL, like https://www.reddit.com/r/TheOwlHouse/comments/gqf70w/my_art_luz_and_amity_when_quarantine_is_over_what/.json
            api_url = '{}.json'.format(url)
            r = requests.get(api_url, headers = {'User-agent': 'RogueStarboard v1.0'}).json()
            url = r[0]["data"]["children"][0]["data"]["url"]
            if url.endswith('.jpg'):
                return url
            else:
                return ''
        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.reddit:
            url = re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', message.content)
            if url and ('reddit.com' in url[0][0] or 'redd.it' in url[0][0]):
                b = self.return_reddit(url[0][0])
                if b:
                    embed=discord.Embed(title='Reddit Embed', description=message.content)
                    embed.set_image(url=b)
                    embed.add_field(name='Sender', value=message.author.mention)
                    await message.channel.send(embed=embed)

    @commands.command(brief='Toggle automatic Reddit embeds.')
    async def embed_reddit(self, ctx):
        if ctx.message.author.id != int(self.db['settings'].find_one(name='owner_id')['value']):
            return

        self.reddit = not self.reddit
        await self.bot.get_user(int(self.db['settings'].find_one(name='owner_id')['value'])).send(self.reddit)
