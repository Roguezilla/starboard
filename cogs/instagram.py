import re
from typing import List

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
	gallery_cache[str(msg.channel_id) + str(msg.id)] = {
		'size': len(data['edge_sidecar_to_children']['edges']),
		'curr': 1
	}

	for i in range(len(data['edge_sidecar_to_children']['edges'])):
		gallery_cache[str(msg.channel_id) + str(msg.id)][i + 1] = data['edge_sidecar_to_children']['edges'][i]['node']['display_url']

	# when repopulating, we need to match the current picture with its index
	if repopulate:
		url = msg.embeds[0].image.__getattribute__('url')
		for key in gallery_cache[str(msg.channel_id) + str(msg.id)]:
			if gallery_cache[str(msg.channel_id) + str(msg.id)][key] == url:
				gallery_cache[str(msg.channel_id) + str(msg.id)]['curr'] = key

async def fix_embed_if_needed(bot: DiscPy, msg_id: str, msg: Message):
	for field in msg.embeds[0].fields:
		if 'Page' in field.__dict__['name']:
			# no need to fix anything when Page field is present in the embed
			return
	
	if msg_id not in gallery_cache:
		url = re.findall(r"\[Jump directly to Instagram\]\((.+)\)", msg.embeds[0].description)
		if populate_cache(Instagram.url_data(url[0]), msg) == 0:
			return

	embed: Embed = msg.embeds[0]
	embed.add_field(name='Page', value=f"{gallery_cache[str(msg.channel_id) + str(msg.id)]['curr']}/{gallery_cache[str(msg.channel_id) + str(msg.id)]['size']}", inline=True)
	await bot.edit_message(msg, embed=embed)

class Instagram(DiscPy.Cog):
	def __init__(self, bot: DiscPy, db: Database):
		@bot.event(self)
		async def on_message(event: Message):
			if event.author.bot or not db['server'].find_one(server_id = event.guild_id):
				return
			
			if url := re.findall(r"^((?:(?:(?:https):(?://)+)(?:www\.)?)instagram\.com/p/.+)$", event.content):
				image, title = Instagram.return_link(url[0], msg=event)
				if image and title:
					embed = Embed(color=0xffcc00, title=title, description=f'[Jump directly to Instagram]({url[0]})')
					embed.set_image(url=image)
					embed.add_field(name='Sender', value=event.author.mention)

					sent: Message = await bot.send_message(event.channel_id, embed=embed.as_json())

					if str(event.channel_id) + str(event.id) in gallery_cache:
						# copy old message info into the new message(our embed) and delete old message from the dictionary
						gallery_cache[str(sent.channel_id) + str(sent.id)] = gallery_cache[str(event.channel_id) + str(event.id)]
						del gallery_cache[str(event.channel_id) + str(event.id)]

						embed: Embed = sent.embeds[0]
						embed.add_field(name='Page', value=f"{gallery_cache[str(sent.channel_id) + str(sent.id)]['curr']}/{gallery_cache[str(sent.channel_id) + str(sent.id)]['size']}", inline=True)
						await bot.edit_message(sent, embed=embed.as_json())
						
						await bot.add_reaction(sent, '⬅️', unicode=True)
						await bot.add_reaction(sent, '➡️', unicode=True)

					# we don't really the message and it only occupies space now
					await bot.delete_message(event)

		@bot.event(self)
		async def on_reaction_add(event: ReactionAddEvent):
			# return if the payload author is the bot or if the payload emote is wrong
			if event.author.bot or not any(e == str(event.emoji) for e in ['➡️', '⬅️']):
				return

			msg: Message = await bot.fetch_message(event.channel_id, event.message_id)
				
			# return if the reacted to message isn't by the bot or if the embed isn't valid
			if msg.author.id != bot.me.user.id or not Instagram.validate_embed(msg.embeds):
				return

			msg_id = str(event.channel_id)+str(event.message_id)

			# we want to repopulate the cache when the bot is restarted
			if msg_id not in gallery_cache:
				url = re.findall(r"\[Jump directly to Instagram\]\((.+)\)", msg.embeds[0].description)
				# see populate_cache
				if populate_cache(Instagram.url_data(url[0]), msg, True) == 0:
					return
			
			if msg_id in gallery_cache:
				embed: Embed = msg.embeds[0]

				await fix_embed_if_needed(bot, msg_id, msg)
					
				gal_size = gallery_cache[msg_id]['size']
				curr_idx = gallery_cache[msg_id]['curr']
				
				if str(event.emoji) == '➡️':
					curr_idx = curr_idx + 1 if curr_idx + 1 <= gal_size else 1
				else:
					curr_idx = curr_idx - 1 if curr_idx - 1 >= 1 else gal_size

				gallery_cache[msg_id]['curr'] = curr_idx
				new_url = gallery_cache[msg_id][curr_idx]

				embed.set_image(url=new_url)
				embed.set_field_at(1, name='Page', value=f"{gallery_cache[str(msg.channel_id) + str(msg.id)]['curr']}/{gallery_cache[str(msg.channel_id) + str(msg.id)]['size']}")

				await bot.edit_message(msg, embed=embed.as_json())
				await bot.remove_reaction(msg, event.author, event.emoji)

	@staticmethod
	def validate_embed(embeds: List[Embed]):
		if embeds:
			return not (embeds[0].description is None) and '[Jump directly to Instagram]' in embeds[0].description
				
		return False
	
	@staticmethod
	def url_data(url):
		# cut out useless stuff and form an api url
		url = url.split('?')[0]
		api_url = url + '?__a=1&__d=dis'
		return requests.get(api_url, headers = {'User-agent': 'RogueStarboard v1.0'}).json()['graphql']['shortcode_media']

	@staticmethod
	def return_link(url, msg: Message):
		data = Instagram.url_data(url)
		# only galeries have edge_sidecar_to_children
		if 'edge_sidecar_to_children' in data:
			# thankfully edge_sidecar_to_children has the images in the right order
			ret = data['edge_sidecar_to_children']['edges'][0]['node']['display_url']
			# as the link is a gallery, we need to populate the gallery cache
			populate_cache(data, msg)
		else:
			ret = data['display_url']
		return (ret, data['owner']['full_name'])