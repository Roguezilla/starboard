import re
from typing import List

import discord
from discord import message
import requests
from discord.ext import commands

import perms

"""
'msgid': {
	'size': 2,
	'curr': 1,
	'1': 'url',
	'2': 'url'
}
"""
gallery_cache = dict()

def populate_cache(data, msg: discord.Message, repopulate=False):
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

async def fix_embed_if_needed(msg_id: str, msg: discord.Message):
	for field in msg.embeds[0].fields:
		if 'Page' in field.__dict__['name']:
			# no need to fix anything when Page field is present in the embed
			return
	
	if msg_id not in gallery_cache:
		url = re.findall(r"\[Jump directly to instagram\]\((.+)\)", msg.embeds[0].description)
		if populate_cache(Instagram.url_data(url[0]), msg) == 0:
			return

	embed: discord.Embed = msg.embeds[0]
	embed.add_field(name='Page', value=f"{gallery_cache[str(msg.channel.id) + str(msg.id)]['curr']}/{gallery_cache[str(msg.channel.id) + str(msg.id)]['size']}", inline=True)
	await msg.edit(embed=embed)

class Instagram(commands.Cog):
	def __init__(self, bot, db):
		self.bot: commands.Bot = bot
		self.db = db

	@staticmethod
	def url_data(url):
		# cut out useless stuff and form an api url
		url = url.split('/?')[0]
		api_url = url + '?__a=1'
		api_return = requests.get(api_url, headers = {'User-agent': 'RogueStarboard v1.0'})
		
		if 'login' not in api_return.url:
			return api_return.json()['graphql']['shortcode_media']
		
		return

	@staticmethod
	def return_link(url, msg=None):
		data = Instagram.url_data(url)
		if data:
			# only galeries have edge_sidecar_to_childrenu
			if 'edge_sidecar_to_children' in data:
				# thankfully edge_sidecar_to_children has the images in the right order
				ret = data['edge_sidecar_to_children']['edges'][0]['node']['display_url']
				# as the link is a gallery, we need to populate the gallery cache
				if msg: populate_cache(data, msg)
			else:
				ret = data['display_url']
		
			return ret
		
		return

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		if (self.db['server'].find_one(server_id = message.guild.id) is None) or message.author.bot:
			return

		if self.db['server'].find_one(server_id = message.guild.id)['instagram_embed'] == 1:
			# TODO maybe replace this monstrocity?
			url = re.findall(r"(\|{0,2}<?[<|]*(?:https?):(?://)+(?:[\w\d_.~\-!*'();:@&=+$,/?#[\]]*)\|{0,2}>?)", message.content)
			
			if url and 'instagram.com/p/' in url[0] and not (url[0].startswith('<') and url[0].endswith('>')) and not (url[0].startswith('||') and url[0].endswith('||')):
				url[0] = url[0].replace('<', '').replace('>', '').replace('|', '')
				ret = self.return_link(url[0], msg=message)
				if ret:
					embed=discord.Embed(color=0xffcc00, description=f'[Jump directly to instagram]({url[0]})\n{message.content.replace(url[0], "").strip()}')
					embed.set_image(url=ret)
					embed.add_field(name='Sender', value=message.author.mention)
					sent: discord.Message = await message.channel.send(embed=embed)

					if str(message.channel.id) + str(message.id) in gallery_cache:
						# copy old message info into the new message(our embed) and delete old message from the dictionary
						gallery_cache[str(sent.channel.id) + str(sent.id)] = gallery_cache[str(message.channel.id) + str(message.id)]
						del gallery_cache[str(message.channel.id) + str(message.id)]

						embed: discord.Embed = sent.embeds[0]
						embed.add_field(name='Page', value=f"{gallery_cache[str(sent.channel.id) + str(sent.id)]['curr']}/{gallery_cache[str(sent.channel.id) + str(sent.id)]['size']}", inline=True)
						await sent.edit(embed=embed)

						await sent.add_reaction('⬅️')
						await sent.add_reaction('➡️')

					# we don't really the message and it only occupies space now
					await message.delete()

	@staticmethod
	def validate_embed(embeds: List[discord.Embed]):
		if embeds:
			if type(embeds[0].description) is discord.embeds._EmptyEmbed:
				return False

			if '[Jump directly to instagram](https://www.instagram.com/' not in embeds[0].description:
				return False

			return True

		return False

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
		# return if the payload author is the bot or if the payload emote is wrong
		if payload.member.bot or not any(e == str(payload.emoji) for e in ['➡️', '⬅️']):
			return

		try:
			msg: discord.Message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
		except:
			return

		# return if the reacted to message isn't by the bot or if the embed isn't valid
		if msg.author.id != self.bot.user.id or not self.validate_embed(msg.embeds):
			return

		msg_id = str(payload.channel_id)+str(payload.message_id)

		# we want to repopulate the cache when the bot is restarted
		if msg_id not in gallery_cache:
			url = re.findall(r"\[Jump directly to instagram\]\((.+)\)", msg.embeds[0].description)
			# see populate_cache
			if populate_cache(Instagram.url_data(url[0]), msg, True) == 0:
				return

		if msg_id in gallery_cache:
			embed: discord.Embed = msg.embeds[0]

			# sometimes embeds break
			await fix_embed_if_needed(msg_id, msg)
				
			gal_size = gallery_cache[msg_id]['size']
			curr_idx = gallery_cache[msg_id]['curr']
			
			if str(payload.emoji) == '➡️':
				curr_idx = curr_idx + 1 if curr_idx + 1 <= gal_size else 1
			else:
				curr_idx = curr_idx - 1 if curr_idx - 1 >= 1 else gal_size

			gallery_cache[msg_id]['curr'] = curr_idx
			new_url = gallery_cache[msg_id][curr_idx]

			embed.set_image(url=new_url)
			embed.set_field_at(1, name='Page', value=f"{gallery_cache[str(msg.channel.id) + str(msg.id)]['curr']}/{gallery_cache[str(msg.channel.id) + str(msg.id)]['size']}")

			await msg.edit(embed=embed)
			await msg.remove_reaction(payload.emoji, payload.member)

	@commands.command(brief='Toggle automatic Instagram embeds.')
	@perms.mod()
	async def instagram(self, ctx: commands.Context):
		if self.db['server'].find_one(server_id = ctx.guild.id) is None:
			return

		prev = self.db['server'].find_one(server_id = ctx.guild.id)['instagram_embed']
		new_val = 0 if prev == 1 else 1
		self.db['server'].update(dict(server_id = str(ctx.guild.id), instagram_embed=new_val), ['server_id'])

		await ctx.send(f"instagram embeds: {'on' if new_val == 1 else 'off'}")