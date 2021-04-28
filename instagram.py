import re

import discord
import requests
from bs4 import BeautifulSoup
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

class Instagram(commands.Cog):
	def __init__(self, bot, db):
		self.bot: commands.Bot = bot
		self.db = db

	@staticmethod
	def url_data(url):
		# cut out useless stuff and form an api url
		url = url.split("?")[0]
		api_url = url + '?__a=1'
		return requests.get(api_url, headers = {'User-agent': 'RogueStarboard v1.0'}).json()['graphql']['shortcode_media']

	@staticmethod
	def return_link(url, msg=None):
		data = Instagram.url_data(url)
		# only galeries have media_metadata
		if 'edge_sidecar_to_children' in data:
			# thankfully edge_sidecar_to_children has the images in the right order
			ret = data['edge_sidecar_to_children']['edges'][0]['node']['display_url']
			# as the link is a gallery, we need to populate the gallery cache
			if msg: populate_cache(data, msg)
		else:
			ret = data['display_url']
		return ret

	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		if message.author.bot:
			return

		if self.db['server'].find_one(server_id = message.guild.id)['instagram_embed'] == 1:
			url = re.findall(r"(\|{0,2}<?[<|]*(?:https?):(?://)+(?:[\w\d_.~\-!*'();:@&=+$,/?#[\]]*)\|{0,2}>?)", message.content)
			if url and 'instagram.com/p/' in url[0] and not (url[0].startswith('<') and url[0].endswith('>')) and not (url[0].startswith('||') and url[0].endswith('||')):
				url[0] = url[0].replace('<', '').replace('>', '').replace('|', '')
				ret = self.return_link(url[0], msg=message)
				if ret:
					embed=discord.Embed(color=0xffcc00, description=f'[Jump to directly instagram]({url[0]})\n{message.content.replace(url[0], "").strip()}')
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

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
		msg_id = str(payload.channel_id)+str(payload.message_id)
		msg: discord.Message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

		# return if the reaction was from a bot or there are no embeds or the message that was reacted to wasn't from the bot
		if payload.member.bot or not msg.embeds or msg.author.id != self.bot.user.id or 'https://www.instagram.com/' not in msg.embeds[0].description:
			return

		# we want to repopulate the cache when the bot is restarted
		if msg_id not in gallery_cache:
			url = re.findall(r"((?:https?):(?://)+(?:[\w\d_.~\-!*'();:@&=+$,/?#[\]]*))", msg.embeds[0].description)
			# see populate_cache
			if populate_cache(Instagram.url_data(url[0]), msg, True) == 0:
				return

		if msg_id in gallery_cache:
			if str(payload.emoji) == '➡️' or str(payload.emoji) == '⬅️':
				embed: discord.Embed = msg.embeds[0]
				
				gal_size = gallery_cache[msg_id]['size']
				curr_idx = gallery_cache[msg_id]['curr']
			
				if str(payload.emoji) == '➡️':
					curr_idx = curr_idx + 1 if curr_idx + 1 <= gal_size else 1
				elif str(payload.emoji) == '⬅️':
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
		prev = self.db['server'].find_one(server_id = ctx.guild.id)['instagram_embed']
		new_val = 0 if prev == 1 else 1
		self.db['server'].update(dict(server_id = str(ctx.guild.id), instagram_embed=new_val), ['server_id'])

		await ctx.send(f"instagram embeds: {'on' if new_val == 1 else 'off'}")