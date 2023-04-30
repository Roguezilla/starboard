import re

import discord
from discord.ext import commands

from db import BotDB

class Twitter(commands.Cog):
	@commands.Cog.listener()
	async def on_message(self, event: discord.Message):
		if event.author.bot or not BotDB.is_setup(event.guild.id):
			return

		if path := re.findall(r'^https?://(?:mobile\.|www\.)?twitter\.com(/[a-zA-Z0-9_]+/status/\d+)(?:\?.+)?$', event.content):
			await event.channel.send(f'https://vxtwitter.com{path[0]}?u={event.author.id}&a={event.author.display_name}')
			await event.delete()