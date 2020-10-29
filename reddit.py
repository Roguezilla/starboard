import re

import discord
import dataset
import requests
from discord.ext import commands

import perms

class Reddit(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
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
    async def on_message(self, message: discord.Message):
        if self.db[str(message.guild.id)].find_one(name='reddit_embed')['value'] == '1':
            url = re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', message.content)
            if url and ('reddit.com' in url[0][0] or 'redd.it' in url[0][0]):
                ret = self.return_reddit(url[0][0])
                if ret:
                    embed=discord.Embed(title='Reddit Embed', description=message.content)
                    embed.set_image(url=ret)
                    embed.add_field(name='Sender', value=message.author.mention)
                    await message.channel.send(embed=embed)

    @commands.command(brief='Toggle automatic Reddit embeds.')
    @perms.mod()
    async def embed_reddit(self, ctx: discord.ext.commands.Context):
        prev = self.db[str(ctx.guild.id)].find_one(name='reddit_embed')['value']
        new_val = '0' if prev == '1' else '1'
        self.db[str(ctx.guild.id)].update(dict(name='reddit_embed', value=new_val), ['name'])

        await self.bot.get_user(ctx.message.author.id).send('reddit embeds: {}'.format('on' if new_val == '1' else 'off'))
