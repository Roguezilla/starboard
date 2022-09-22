import re

from dataset import Database
from discpy.discpy import DiscPy
from discpy.message import Message

class Twitter(DiscPy.Cog):
	def __init__(self, bot: DiscPy, db: Database):
		@bot.event(self)
		async def on_message(event: Message):
			if event.author.bot or not db['server'].find_one(server_id = event.guild_id) or not event.embeds:
				return

			if not event.embeds[0].video:
				return

			if path := re.findall(r'^https://(?:mobile.)?twitter\.com(/.+/status/\d+)$', event.content):
				await bot.send_message(event.channel_id, f'https://vxtwitter.com{path[0]}?u={event.author.id}')
				await bot.delete_message(event)