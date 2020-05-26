import discord
import json
import requests
import re
from discord.ext import commands

class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        cfg = json.load(open('bot.json'))
        if str(message.guild.id) in cfg and cfg[str(message.guild.id)]['reddit'] == True:
            url = re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', message.content)
            if url and ("reddit.com" in url[0][0] or "redd.it" in url[0][0]):
                b = self.return_reddit(url[0][0])
                if b:
                    embed=discord.Embed(title="Reddit Embed", description=message.content)
                    embed.set_image(url=b)
                    await message.channel.send(embed=embed)
    
    @commands.command(brief='Toggle automatic Reddit embeds.')
    @commands.has_permissions(administrator=True)
    async def embed_reddit(self, ctx):
        cfg = json.load(open('bot.json'))
        if str(ctx.guild.id) not in cfg:
            await ctx.send("Please set up the bot with <>setup archive_channel archive_emote archive_emote_amount.")
            return
        
        if 'reddit' in cfg[str(ctx.message.guild.id)]:
            if cfg[str(ctx.message.guild.id)]['reddit'] == True:
                cfg[str(ctx.message.guild.id)].update({'reddit' : False})
                b = 'disabled'
            else:
                cfg[str(ctx.message.guild.id)].update({'reddit' : True})
                b = 'enabled'
        else:
            cfg[str(ctx.message.guild.id)].update({'reddit' : True})
            b = "enabled"

        json.dump(cfg, open('bot.json', 'w'), indent=4)
        
        await ctx.send("Succesfully changed embed state to: \"{}\"".format(b))
