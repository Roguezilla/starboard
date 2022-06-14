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
	if 'media_metadata' not in data:
		# if data doesn't have media_metadata, then it's not a gallery
		return 0

	gallery_cache[str(msg.channel_id) + str(msg.id)] = {
		'size': len(data['gallery_data']['items']),
		'curr': 1
	}

	for i in range(len(data['gallery_data']['items'])):
		idx = data['gallery_data']['items'][i]['media_id']
		gallery_cache[str(msg.channel_id) + str(msg.id)][i + 1] = data['media_metadata'][idx]['s']['u'].replace('&amp;', '&')

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
		url = re.findall(r"\[Jump directly to reddit\]\((.+)\)", msg.embeds[0].description)
		if populate_cache(Reddit.url_data(url[0]), msg) == 0:
			return

	embed: Embed = msg.embeds[0]
	embed.add_field(name='Page', value=f"{gallery_cache[str(msg.channel_id) + str(msg.id)]['curr']}/{gallery_cache[str(msg.channel_id) + str(msg.id)]['size']}", inline=True)
	await bot.edit(msg.channel_id, msg.id, embed=embed)

class Reddit(DiscPy.Cog):
	def __init__(self, bot: DiscPy, db: Database):
		@bot.event(self)
		async def on_message(ctx: DiscPy, event: Message):
			if event.author.bot or not db['server'].find_one(server_id = event.guild_id):
				return
			
			if url := re.findall(r"((?:(?:(?:https):(?://)+)(?:www\.)?)redd(?:it\.com/|\.it/).+)", event.content):
				image, title = Reddit.return_link(url[0], msg=event)
				if image and title:
					embed = Embed(color=0xffcc00, title=title, description=f'[Jump directly to reddit]({url[0]})\n{event.content.replace(url[0], "")}')
					embed.set_image(url=image)
					embed.add_field(name='Sender', value=event.author.mention)

					sent: Message = await ctx.send_message(event.channel_id, embed=embed.as_json())

					if str(event.channel_id) + str(event.id) in gallery_cache:
						# copy old message info into the new message(our embed) and delete old message from the dictionary
						gallery_cache[str(sent.channel_id) + str(sent.id)] = gallery_cache[str(event.channel_id) + str(event.id)]
						del gallery_cache[str(event.channel_id) + str(event.id)]

						embed: Embed = sent.embeds[0]
						embed.add_field(name='Page', value=f"{gallery_cache[str(sent.channel_id) + str(sent.id)]['curr']}/{gallery_cache[str(sent.channel_id) + str(sent.id)]['size']}", inline=True)
						await ctx.edit_message(sent, embed=embed.as_json())
						
						await ctx.add_reaction(sent, '⬅️', unicode=True)
						await ctx.add_reaction(sent, '➡️', unicode=True)

					# we don't really the message and it only occupies space now
					await ctx.delete_message(event)

		@bot.event(self)
		async def on_reaction_add(ctx: DiscPy, event: ReactionAddEvent):
			# return if the payload author is the bot or if the payload emote is wrong
			if event.author.bot or not any(e == str(event.emoji) for e in ['➡️', '⬅️']):
				return

			msg: Message = await ctx.fetch_message(event.channel_id, event.message_id)
				
			# return if the reacted to message isn't by the bot or if the embed isn't valid
			if msg.author.id != ctx.me.user.id or not Reddit.validate_embed(msg.embeds):
				return

			msg_id = str(event.channel_id)+str(event.message_id)

			# we want to repopulate the cache when the bot is restarted
			if msg_id not in gallery_cache:
				url = re.findall(r"\[Jump directly to reddit\]\((.+)\)", msg.embeds[0].description)
				# see populate_cache
				if populate_cache(Reddit.url_data(url[0]), msg, True) == 0:
					return
			
			if msg_id in gallery_cache:
				embed: Embed = msg.embeds[0]

				await fix_embed_if_needed(ctx, msg_id, msg)
					
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

				await ctx.edit_message(msg, embed=embed.as_json())
				await ctx.remove_reaction(msg, event.author, event.emoji)

	@staticmethod
	def validate_embed(embeds: List[Embed]):
		if embeds:
			return not (embeds[0].description is None) and '[Jump directly to reddit]' in embeds[0].description
				
		return False
	
	@staticmethod
	def url_data(url):
		# cut out useless stuff and form an api url
		if 'redd.it' in url:
			# redd.it redirect stuff
			url = requests.head(url, allow_redirects=True).url
		else:
			url = url.split("?")[0]
			
		return requests.get(url + '.json', headers = {'User-agent': 'discpy'}).json()[0]['data']['children'][0]['data']

	@staticmethod
	def return_link(url, msg=None):
		data = Reddit.url_data(url)
		# only galeries have media_metadata
		if 'media_metadata' in data:
			# media_metadata is unordered, gallery_data has the right order
			first = data['gallery_data']['items'][0]['media_id']
			# the highest quality pic always the last one
			ret = data['media_metadata'][first]['s']['u'].replace('&amp;', '&')
			# as the link is a gallery, we need to populate the gallery cache
			if msg: populate_cache(data, msg)
		else:
			# covers gifs
			ret = data['url_overridden_by_dest']
			# the url doesn't end with any of these then the post is a video, so fallback to the thumbnail
			if '.jpg' not in ret and '.png' not in ret and '.gif' not in ret:
				ret = data['preview']['images'][0]['source']['url'].replace('&amp;', '&')
		return (ret, data["title"])
