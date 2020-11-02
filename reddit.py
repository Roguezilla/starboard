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
        # Form an API URL, like https://www.reddit.com/r/TheOwlHouse/comments/gqf70w/my_art_luz_and_amity_when_quarantine_is_over_what/.json
        api_url = '{}.json'.format(url)
        r = requests.get(api_url, headers = {'User-agent': 'RogueStarboard v1.0'}).json()
        # only galeries have media_metadata
        if 'media_metadata' in r[0]['data']['children'][0]['data']:
            # media_metadata is unordered, gallery_data has the right order
            first = r[0]['data']['children'][0]['data']['gallery_data']['items'][0]['media_id']
            # the highest quality pic always the last one
            ret = r[0]['data']['children'][0]['data']['media_metadata'][first]['s']['u'].replace('&amp;', '&')
        else:
            # covers gifs
            ret = r[0]['data']['children'][0]['data']['url_overridden_by_dest']
            # the url doesn't end with any of these then the post is a video, so fallback to the thumbnail
            if '.jpg' not in ret and '.png' not in ret and '.gif' not in ret:
                ret = r[0]['data']['children'][0]['data']['preview']['images'][0]['source']['url'].replace('&amp;', '&')
        return ret

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.db[str(message.guild.id)].find_one(name='reddit_embed')['value'] == '1':
            url = re.findall(r'(<?(https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*>?)', message.content)
            if url and ('reddit.com' in url[0][0] or 'redd.it' in url[0][0]) and (url[0][0][0] != '<' and url[0][0][-1] != '>'):
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
