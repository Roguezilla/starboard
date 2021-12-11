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
			if (db['server'].find_one(server_id = event.guild_id) is None) or event.author.bot:
				return
			
			if db['server'].find_one(server_id = event.guild_id)['reddit_embed'] == 1:
				url = re.findall(r"(\|{0,2}<?)?((?:(?:(?:https?):(?://)+)(?:www\.)?)redd(?:it\.com/|\.it/).+[^|>])(\|{0,2}>?)?", event.content)
				# [(|| or < or '', url, || or > or '')]
				if url and not ((url[0][0] == '<' and url[0][2] == '>') or (url[0][0] == '||' and url[0][2] == '||')):
					image, title = Reddit.return_link(url[0][1], msg=event)
					if image:
						embed = Embed(color=0xffcc00, title=title, description=f'[Jump directly to reddit]({url[0][1]})\n{event.content.replace(url[0][1], "")}')
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
							
							await bot.add_reaction(sent, '⬅️')
							await bot.add_reaction(sent, '➡️')

						# we don't really the message and it only occupies space now
						await bot.delete_message(event)

		@staticmethod
		def validate_embed(embeds: List[Embed]):
			if embeds:
				return not (embeds[0].description is None) and '[Jump directly to reddit](https://www.reddit.com/r/' in embeds[0].description
				
			return False

		@bot.event(self)
		async def on_reaction_add(ctx: DiscPy, event: ReactionAddEvent):
			# return if the payload author is the bot or if the payload emote is wrong
			if event.author.bot or not any(e == str(event.emoji) for e in ['➡️', '⬅️']):
				return

			try:
				msg: Message = await bot.fetch_message(event.channel_id, event.message_id)
			except:
				return

			# return if the reacted to message isn't by the bot or if the embed isn't valid
			if msg.author.id != bot.me.user.id or not validate_embed(msg.embeds):
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

		@bot.command()
		@bot.permissions(perms.is_mod)
		async def reddit(ctx: DiscPy, event: Message):
			if db['server'].find_one(server_id = event.guild_id) is None:
				return

			prev = db['server'].find_one(server_id = event.guild_id)['reddit_embed']
			new_val = 0 if prev == 1 else 1
			db['server'].update(dict(server_id = str(event.guild_id), reddit_embed=new_val), ['server_id'])

			await ctx.send_message(event.channel_id, f"reddit embeds: {'on' if new_val == 1 else 'off'}")
	
	@staticmethod
	def url_data(url):
		# cut out useless stuff and form an api url
		if 'redd.it' in url:
			# redd.it redirect stuff
			url = requests.head(url, allow_redirects=True).url
		else:
			url = url.split("?")[0]
			
		api_url = url + '.json'
		return requests.get(api_url, headers = {'User-agent': 'RogueStarboard v1.0'}).json()[0]['data']['children'][0]['data']

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
