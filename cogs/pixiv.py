import re

import discord
from discord.ext import commands

from db import BotDB

class Pixiv(commands.Cog):
	@commands.Cog.listener()
	async def on_message(self, event: discord.Message):
		if event.author.bot or not BotDB.is_setup(event.guild.id):
			return

		if id := re.findall(r'^https?://(?:www\.)?pixiv\.net/(?:en/)?artworks/(\d+)$', event.content):
			await event.channel.send(f'https://pixiv.kmn5.li/{id[0]}?u={event.author.id}&a={event.author.display_name}')
			await event.delete()