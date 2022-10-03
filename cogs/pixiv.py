import re

from dataset import Database
from discpy.discpy import DiscPy
from discpy.message import Message

class BetterPixiv(DiscPy.Cog):
	def __init__(self, bot: DiscPy, db: Database):
		@bot.event(self)
		async def on_message(event: Message):
			if event.author.bot or not db['server'].find_one(server_id = event.guild_id):
				return

			if id := re.findall(r'^https:\/\/(?:www\.)?pixiv\.net\/(?:en\/)?artworks\/(\d+)$', event.content):
				await bot.send_message(event.channel_id, f'https://pixiv.kmn5.li/{id[0]}?u={event.author.id}')
				await bot.delete_message(event)