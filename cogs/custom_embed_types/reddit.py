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
class Reddit:
	cache = dict()

	@staticmethod
	def str():
		return "Reddit"

	@staticmethod
	def regex():
		return r"^((?:(?:(?:https):(?://)+)(?:www\.)?)(redd)(?:it\.com/|\.it/).+)$"

	@staticmethod
	def build_cache(data, msg: Message, repopulate=False):
		Reddit.cache[str(msg.channel_id) + str(msg.id)] = {
			'curr': 0,
			'images': []
		}

		for i in range(len(data['gallery_data']['items'])):
			media_id = data['gallery_data']['items'][i]['media_id']
			Reddit.cache[str(msg.channel_id) + str(msg.id)]['images'].append(data['media_metadata'][media_id]['s']['u'].replace('&amp;', '&'))

		# when repopulating, we need to match the current picture with its index
		if repopulate:
			for i in range(len(Reddit.cache[str(msg.channel_id) + str(msg.id)]['images'])):
				if Reddit.cache[str(msg.channel_id) + str(msg.id)]['images'][i] == msg.embeds[0].image.url:
					Reddit.cache[str(msg.channel_id) + str(msg.id)]['curr'] = i
	
	@staticmethod
	def validate_embed(embeds: List[Embed]) -> bool:
		if not embeds: return False
		if not re.findall(f"{Reddit.regex()}", embeds[0].url): return False
		if not (len(embeds[0].fields) == 2 and embeds[0].fields[1].name == "Page"): return False
				
		return True
	
	@staticmethod
	def url_data(url):
		if 'redd.it' in url:
			# redd.it redirect stuff
			url = DiscPy.session.head(url, allow_redirects=True).url
		else: url = url.split("?")[0]
			
		return DiscPy.session.get(url + '.json', headers = {'User-agent': 'discpy'}).json()[0]['data']['children'][0]['data']

	@staticmethod
	def return_link(url, msg):
		data = Reddit.url_data(url)
		# only galeries have media_metadata
		if 'media_metadata' in data:
			# media_metadata is unordered, gallery_data has the right order
			first = data['gallery_data']['items'][0]['media_id']
			# the highest quality pic always the last one
			ret = data['media_metadata'][first]['s']['u'].replace('&amp;', '&')
			# as the link is a gallery, we need to populate the gallery cache
			Reddit.build_cache(data, msg)
		else:
			# covers gifs
			ret = data['url_overridden_by_dest']
			# the url doesn't end with any of these then the post is a video, so fallback to the thumbnail
			if '.jpg' not in ret and '.png' not in ret and '.gif' not in ret:
				ret = data['preview']['images'][0]['source']['url'].replace('&amp;', '&')
		
		return (ret, data['title'])
