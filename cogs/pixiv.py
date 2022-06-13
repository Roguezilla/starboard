import re

from dataset import Database
from discpy.discpy import DiscPy
from discpy.message import Message

class Pixiv(DiscPy.Cog):
	def __init__(self, bot: DiscPy, db: Database):
		@bot.event(self)
		async def on_message(ctx: DiscPy, event: Message):
			if not db['server'].find_one(server_id = event.guild_id) or event.author.bot:
				return

			# when someone puts the link between <>
			if not event.embeds:
				return

			if id := re.findall(r'https:\/\/www\.pixiv\.net\/(?:en\/)?artworks\/(\d+)', event.content):
				await bot.send_message(event.channel_id, f'https://pixiv.kmn5.li/{id[0]}?u={event.author.id}')
				await bot.delete_message(event)