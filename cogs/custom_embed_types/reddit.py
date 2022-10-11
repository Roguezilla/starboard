import re
from typing import List

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
class Reddit:
	gallery_cache = dict()

	@staticmethod
	def str():
		return "Reddit"

	@staticmethod
	def regex():
		return r"^((?:(?:(?:https):(?://)+)(?:www\.)?)(redd)(?:it\.com/|\.it/).+)$"

	@staticmethod
	def populate_cache(data, msg: Message, repopulate=False):
		if 'media_metadata' not in data:
			# if data doesn't have media_metadata, then it's not a gallery
			return 0

		Reddit.gallery_cache[str(msg.channel_id) + str(msg.id)] = {
			'size': len(data['gallery_data']['items']),
			'curr': 1
		}

		for i in range(len(data['gallery_data']['items'])):
			idx = data['gallery_data']['items'][i]['media_id']
			Reddit.gallery_cache[str(msg.channel_id) + str(msg.id)][i + 1] = data['media_metadata'][idx]['s']['u'].replace('&amp;', '&')

		# when repopulating, we need to match the current picture with its index
		if repopulate:
			url = msg.embeds[0].image.__getattribute__('url')
			for key in Reddit.gallery_cache[str(msg.channel_id) + str(msg.id)]:
				if Reddit.gallery_cache[str(msg.channel_id) + str(msg.id)][key] == url:
					Reddit.gallery_cache[str(msg.channel_id) + str(msg.id)]['curr'] = key

	@staticmethod
	async def fix_embed_if_needed(bot: DiscPy, msg_id: str, msg: Message):
		for field in msg.embeds[0].fields:
			if 'Page' in field.__dict__['name']:
				# no need to fix anything when Page field is present in the embed
				return
		
		if msg_id not in Reddit.gallery_cache:
			url = re.findall(r"\[Jump directly to reddit\]\((.+)\)", msg.embeds[0].description)
			if Reddit.populate_cache(Reddit.url_data(url[0]), msg) == 0:
				return

		embed: Embed = msg.embeds[0]
		embed.add_field(name='Page', value=f"{Reddit.gallery_cache[str(msg.channel_id) + str(msg.id)]['curr']}/{Reddit.gallery_cache[str(msg.channel_id) + str(msg.id)]['size']}", inline=True)
		await bot.edit_message(msg, embed=embed)
	
	@staticmethod
	def validate_embed(embeds: List[Embed]):
		if embeds:
			return not (embeds[0].description is None) and f'[Jump directly to {Reddit.str()}]' in embeds[0].description
				
		return False
	
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
			Reddit.populate_cache(data, msg)
		else:
			# covers gifs
			ret = data['url_overridden_by_dest']
			# the url doesn't end with any of these then the post is a video, so fallback to the thumbnail
			if '.jpg' not in ret and '.png' not in ret and '.gif' not in ret:
				ret = data['preview']['images'][0]['source']['url'].replace('&amp;', '&')
		
		return (ret, data['title'])
