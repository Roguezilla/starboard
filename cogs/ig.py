import re

import perms
import requests
from dataset import Database
from discpy.discpy import DiscPy
from discpy.events import ReactionAddEvent
from discpy.message import Embed, Message

"""
'msgid': {
	'size': 2,
	'curr': 1,
	'1': 'url',
	'2': 'url'
}
"""
gallery_cache = dict()

def populate_cache(data, msg: Message, repopulate=False):
	if 'edge_sidecar_to_children' not in data:
		# if data doesn't have media_metadata, then it's not a gallery
		return 0

	gallery_cache[str(msg.channel.id) + str(msg.id)] = {
		'size': len(data['edge_sidecar_to_children']['edges']),
		'curr': 1
	}

	for i in range(len(data['edge_sidecar_to_children']['edges'])):
		gallery_cache[str(msg.channel.id) + str(msg.id)][i + 1] = data['edge_sidecar_to_children']['edges'][i]['node']['display_url']

	# when repopulating, we need to match the current picture with its index
	if repopulate:
		url = msg.embeds[0].image.__getattribute__('url')
		for key in gallery_cache[str(msg.channel.id) + str(msg.id)]:
			if gallery_cache[str(msg.channel.id) + str(msg.id)][key] == url:
				gallery_cache[str(msg.channel.id) + str(msg.id)]['curr'] = key

async def fix_embed_if_needed(bot: DiscPy, msg_id: str, msg: Message):
	for field in msg.embeds[0].fields:
		if 'Page' in field.__dict__['name']:
			# no need to fix anything when Page field is present in the embed
			return
	
	if msg_id not in gallery_cache:
		url = re.findall(r"\[Jump directly to instagram\]\((.+)\)", msg.embeds[0].description)
		if populate_cache(Instagram.url_data(url[0]), msg) == 0:
			return

	embed: Embed = msg.embeds[0]
	embed.add_field(name='Page', value=f"{gallery_cache[str(msg.channel.id) + str(msg.id)]['curr']}/{gallery_cache[str(msg.channel.id) + str(msg.id)]['size']}", inline=True)
	await bot.edit(msg.channel_id, msg.id, embed=embed)


class Instagram(DiscPy.Cog):
	def __init__(self, bot: DiscPy, db: Database):
		@bot.event(self)
		async def on_reaction_add(ctx: DiscPy, event: ReactionAddEvent):
			pass
			
		@bot.event(self)
		async def on_message(ctx: DiscPy, event: Message):
			pass