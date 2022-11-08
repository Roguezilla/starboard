import re
from typing import List

from discpy.discpy import DiscPy
from discpy.message import Embed, Message

"""
'msgid': {
	'curr': 0,
	'images': []
}
"""
class Instagram:
	cache = dict()

	@staticmethod
	def str():
		return "Instagram"

	@staticmethod
	def regex():
		return r"^((?:(?:(?:https):(?://)+)(?:www\.)?)(instagram)\.com/p/.+)$"

	@staticmethod
	def build_cache(data, msg: Message, repopulate=False):
		Instagram.cache[str(msg.channel_id) + str(msg.id)] = {
			'curr': 0,
			'images': []
		}

		for i in range(len(data['edge_sidecar_to_children']['edges'])):
			Instagram.cache[str(msg.channel_id) + str(msg.id)]['images'].append(data['edge_sidecar_to_children']['edges'][i]['node']['display_url'])

		# when repopulating, we need to match the current picture with its index
		if repopulate:
			for i in range(len(Instagram.cache[str(msg.channel_id) + str(msg.id)]['images'])):
				if Instagram.cache[str(msg.channel_id) + str(msg.id)]['images'][i] == msg.embeds[0].image.url:
					Instagram.cache[str(msg.channel_id) + str(msg.id)]['curr'] = i
					break

	@staticmethod
	def validate_embed(embeds: List[Embed]) -> bool:
		if not embeds: return False
		if not re.findall(f"{Instagram.regex()}", embeds[0].url): return False
		if not (len(embeds[0].fields) == 2 and embeds[0].fields[1].name == "Page"): return False
				
		return True
	
	@staticmethod
	def url_data(url):
		# cut out useless stuff so we can form an api url
		url = url.split('?')[0]
		# &__d=dis somehow makes it work again
		api_url = url + '?__a=1&__d=dis'
		return DiscPy.session.get(api_url, headers = {'User-agent': 'RogueStarboard v1.0'}).json()['graphql']['shortcode_media']

	@staticmethod
	def return_link(url, msg):
		data = Instagram.url_data(url)
		# only galeries have edge_sidecar_to_children
		if 'edge_sidecar_to_children' in data:
			# thankfully edge_sidecar_to_children has the images in the right order
			ret = data['edge_sidecar_to_children']['edges'][0]['node']['display_url']
			# as the link is a gallery, we need to populate the gallery cache
			Instagram.build_cache(data, msg)
		else:
			ret = data['display_url']
		
		return (ret, data['owner']['full_name'])
