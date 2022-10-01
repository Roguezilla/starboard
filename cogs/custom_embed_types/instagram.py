import re
from typing import List

import requests
from discpy.discpy import DiscPy
from discpy.message import Embed, Message

"""
'msgid': {
	'size': 2,
	'curr': 1,
	'1': 'url',
	'2': 'url'
}
"""
class Instagram:
	gallery_cache = dict()

	@staticmethod
	def str():
		return "Instagram"

	@staticmethod
	def regex():
		return r"^((?:(?:(?:https):(?://)+)(?:www\.)?)(instagram)\.com/p/.+)$"

	@staticmethod
	def populate_cache(data, msg: Message, repopulate=False):
		Instagram.gallery_cache[str(msg.channel_id) + str(msg.id)] = {
			'size': len(data['edge_sidecar_to_children']['edges']),
			'curr': 1
		}

		for i in range(len(data['edge_sidecar_to_children']['edges'])):
			Instagram.gallery_cache[str(msg.channel_id) + str(msg.id)][i + 1] = data['edge_sidecar_to_children']['edges'][i]['node']['display_url']

		# when repopulating, we need to match the current picture with its index
		if repopulate:
			url = msg.embeds[0].image.__getattribute__('url')
			for key in Instagram.gallery_cache[str(msg.channel_id) + str(msg.id)]:
				if Instagram.gallery_cache[str(msg.channel_id) + str(msg.id)][key] == url:
					Instagram.gallery_cache[str(msg.channel_id) + str(msg.id)]['curr'] = key

	@staticmethod
	async def fix_embed_if_needed(bot: DiscPy, msg_id: str, msg: Message):
		for field in msg.embeds[0].fields:
			if 'Page' in field.__dict__['name']:
				# no need to fix anything when Page field is present in the embed
				return
		
		if msg_id not in Instagram.gallery_cache:
			url = re.findall(r"\[Jump directly to Instagram\]\((.+)\)", msg.embeds[0].description)
			if Instagram.populate_cache(Instagram.url_data(url[0]), msg) == 0:
				return

		embed: Embed = msg.embeds[0]
		embed.add_field(name='Page', value=f"{Instagram.gallery_cache[str(msg.channel_id) + str(msg.id)]['curr']}/{Instagram.gallery_cache[str(msg.channel_id) + str(msg.id)]['size']}", inline=True)
		await bot.edit_message(msg, embed=embed)

	@staticmethod
	def validate_embed(embeds: List[Embed]):
		if embeds:
			return not (embeds[0].description is None) and f'[Jump directly to {Instagram.str()}]' in embeds[0].description
				
		return False
	
	@staticmethod
	def url_data(url):
		# cut out useless stuff so we can form an api url
		url = url.split('?')[0]
		# &__d=dis somehow makes it work again
		api_url = url + '?__a=1&__d=dis'
		return requests.get(api_url, headers = {'User-agent': 'RogueStarboard v1.0'}).json()['graphql']['shortcode_media']

	@staticmethod
	def return_link(url, msg):
		data = Instagram.url_data(url)
		# only galeries have edge_sidecar_to_children
		if 'edge_sidecar_to_children' in data:
			# thankfully edge_sidecar_to_children has the images in the right order
			ret = data['edge_sidecar_to_children']['edges'][0]['node']['display_url']
			# as the link is a gallery, we need to populate the gallery cache
			Instagram.populate_cache(data, msg)
		else:
			ret = data['display_url']
		
		return (ret, data['owner']['full_name'])
