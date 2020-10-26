import re

import discord
import dataset
import requests
from bs4 import BeautifulSoup
from discord.ext import commands

import perms

class Instagram(commands.Cog):
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.db[str(message.guild.id)].find_one(name='instagram_embed')['value'] == '1':
            url = re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', message.content)
            if url and 'instagram.com/p/' in url[0][0]:
                embed=discord.Embed(title='Instagram embed', description=message.content)
                embed.set_image(url=BeautifulSoup(requests.get(url[0][0].replace('mobile.', '')).text, 'html.parser').find('meta', attrs={'property':'og:image'}).get('content'))
                embed.add_field(name='Sender', value=message.author.mention)
                await message.channel.send(embed=embed)

    @commands.command(brief='Toggle automatic Instagram embeds.')
    @perms.mod()
    async def embed_insta(self, ctx):
        prev = self.db[str(ctx.guild.id)].find_one(name='instagram_embed')['value']
        new_val = '0' if prev == '1' else '1'
        self.db[str(ctx.guild.id)].update(dict(name='instagram_embed', value=new_val), ['name'])
