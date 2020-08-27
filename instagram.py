import re

import discord
import dataset
import requests
from bs4 import BeautifulSoup
from discord.ext import commands


class Instagram(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.insta = False
        self.db = db

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.insta:
            url = re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', message.content)
            if url and 'instagram.com/p/' in url[0][0]:
                embed=discord.Embed(title='Instagram embed', description=message.content)
                embed.set_image(url=BeautifulSoup(requests.get(url[0][0].replace('mobile.', '')).text, 'html.parser').find('meta', attrs={'property':'og:image'}).get('content'))
                embed.add_field(name='Sender', value=message.author.mention)
                await message.channel.send(embed=embed)

    @commands.command(brief='Toggle automatic Instagram embeds.')
    async def embed_insta(self, ctx):
        if ctx.message.author.id != int(self.db['settings'].find_one(name='owner_id')['value']):
            return

        self.insta = not self.insta
        await self.bot.get_user(int(self.db['settings'].find_one(name='owner_id')['value'])).send(self.insta)
