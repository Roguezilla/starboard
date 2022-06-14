import re

from dataset import Database
from discpy.discpy import DiscPy
from discpy.message import Message

class Pixiv(DiscPy.Cog):
	def __init__(self, bot: DiscPy, db: Database):
		@bot.event(self)
		async def on_message(ctx: DiscPy, event: Message):
			if event.author.bot or not db['server'].find_one(server_id = event.guild_id):
				return

			if id := re.findall(r'https:\/\/(?:www\.)?pixiv\.net\/(?:en\/)?artworks\/(\d+)', event.content):
				await ctx.send_message(event.channel_id, f'https://pixiv.kmn5.li/{id[0]}?u={event.author.id}')
				await ctx.delete_message(event)