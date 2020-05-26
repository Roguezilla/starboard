import discord
import json
import re
import requests
from bs4 import BeautifulSoup
from discord.ext import commands

class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        cfg = json.load(open('bot.json'))
        if str(message.guild.id) in cfg and cfg[str(message.guild.id)]['insta'] == True:
            url = re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', message.content)
            if url and "instagram.com" in url[0][0]:
                embed=discord.Embed(title="Reddit Embed", description=message.content)
                embed.set_image(url=BeautifulSoup(requests.get(url[0][0].replace('mobile.', '')).text, 'html.parser').find('meta', attrs={'property':'og:image'}).get('content'))
                await message.channel.send(embed=embed)

    @commands.command(brief='Toggle automatic Instagram embeds.')
    @commands.has_permissions(administrator=True)
    async def embed_insta(self, ctx):
        cfg = json.load(open('bot.json'))
        if str(ctx.guild.id) not in cfg:
            await ctx.send("Please set up the bot with <>setup archive_channel archive_emote archive_emote_amount.")
            return
        
        if 'insta' in cfg[str(ctx.message.guild.id)]:
            if cfg[str(ctx.message.guild.id)]['insta'] == True:
                cfg[str(ctx.message.guild.id)].update({'insta' : False})
                b = 'disabled'
            else:
                cfg[str(ctx.message.guild.id)].update({'insta' : True})
                b = 'enabled'
        else:
            cfg[str(ctx.message.guild.id)].update({'insta' : True})
            b = "enabled"

        json.dump(cfg, open('bot.json', 'w'), indent=4)
        
        await ctx.send("Succesfully changed embed state to: \"{}\"".format(b))
