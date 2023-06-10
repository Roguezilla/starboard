import re
from typing import List

import discord
import requests
from discord.ext import commands
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from db import BotDB

"""
'msgid': {
	'curr': 0,
	'images': []
}
"""
class Instagram(commands.Cog):
	__cache = dict()

	__session = requests.Session()
	__session.mount('https://', HTTPAdapter(max_retries=Retry(
		total=10,
		status_forcelist=[429],
		method_whitelist=None,
		respect_retry_after_header=True
	)))

	__regex = r'^https?://(?:www\.)?instagram\.com/p/[a-zA-Z0-9/]+$'

	def __init__(self, bot):
		self.bot: commands.Bot = bot

	@staticmethod
	def __build_cache(data, msg: discord.Message, repopulate=False):
		Instagram.__cache[str(msg.channel.id) + str(msg.id)] = {
			'curr': 0,
			'images': []
		}

		for i in range(len(data['edge_sidecar_to_children']['edges'])):
			Instagram.__cache[str(msg.channel.id) + str(msg.id)]['images'].append(data['edge_sidecar_to_children']['edges'][i]['node']['display_url'])

		# when repopulating, we need to match the current picture with its index
		if repopulate:
			for i in range(len(Instagram.__cache[str(msg.channel.id) + str(msg.id)]['images'])):
				if Instagram.__cache[str(msg.channel.id) + str(msg.id)]['images'][i] == msg.embeds[0].image.url:
					Instagram.__cache[str(msg.channel.id) + str(msg.id)]['curr'] = i
					break

	@staticmethod
	def __url_data(url):
		# cut out useless stuff so we can form an api url
		url = url.split('?')[0]
		# &__d=dis somehow makes it work again
		api_url = url + '?__a=1&__d=dis'
		return Instagram.__session.get(api_url, headers = {'User-agent': 'RogueStarboard v1.0'}).json()['graphql']['shortcode_media']

	@staticmethod
	def get_data(url, msg):
		data = Instagram.__url_data(url)
		# only galeries have edge_sidecar_to_children
		if 'edge_sidecar_to_children' in data:
			# thankfully edge_sidecar_to_children has the images in the right order
			ret = data['edge_sidecar_to_children']['edges'][0]['node']['display_url']
			# as the link is a gallery, we need to populate the gallery cache
			Instagram.__build_cache(data, msg)
		else:
			ret = data['display_url']

		return (ret, data['owner']['full_name'])

	@commands.Cog.listener()
	async def on_message(self, event: discord.Message):
		if not BotDB.is_setup(event.guild.id) or event.author.bot:
			return

		if match := re.findall(Instagram.__regex, event.content):
			if data := Instagram.get_data(match[0], msg=event):
				embed = discord.Embed(color=0xffcc00, title=data[1], url=match[0])
				embed.set_image(url=data[0])
				embed.add_field(name='Original Poster', value=event.author.mention)

				sent = await event.channel.send(embed=embed)

				if str(event.channel.id) + str(event.id) in Instagram.__cache:
					key = str(sent.channel.id) + str(sent.id)
					# copy original message cache into the new message(our embed) and delete the original message from the cache
					Instagram.__cache[key] = Instagram.__cache[str(event.channel.id) + str(event.id)]
					del Instagram.__cache[str(event.channel.id) + str(event.id)]

					sent.embeds[0].add_field(name='Page', value=f"{Instagram.__cache[key]['curr'] + 1}/{len(Instagram.__cache[key]['images'])}")
					await sent.edit(embed=sent.embeds[0])

					await sent.add_reaction('⬅️')
					await sent.add_reaction('➡️')

				# we don't really the message and it only occupies space now
				await event.delete()

	@staticmethod
	def validate_embed(embeds: List[discord.Embed]) -> bool:
		if not embeds: return False
		if not re.findall(Instagram.__regex, embeds[0].url): return False
		if len(embeds[0].fields) == 2 and not embeds[0].fields[1].name == "Page": return False

		return True

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, event: discord.RawReactionActionEvent):
		# return if the payload author is the bot or if the payload emote is wrong
		if event.member.bot or not any(e == str(event.emoji) for e in ['➡️', '⬅️']):
			return

		msg = await self.bot.get_channel(event.channel_id).fetch_message(event.message_id)

		# return if the reacted to message isn't by the bot or if the embed isn't valid
		if msg.author.id != self.bot.user.id:
			return

		if not self.validate_embed(msg.embeds):
			return

		key = str(event.channel_id)+str(event.message_id)

		# the gallery cache gets wiped when the bot is turned off, so we have to rebuild it
		if key not in Instagram.__cache:
			Instagram.__build_cache(Instagram.__url_data(msg.embeds[0].url), msg, True)

		if key in Instagram.__cache:
			gal_size = len(Instagram.__cache[key]['images'])
			curr_idx = Instagram.__cache[key]['curr']

			if str(event.emoji) == '➡️':
				curr_idx = curr_idx + 1 if curr_idx + 1 < gal_size else 0
			else:
				curr_idx = curr_idx - 1 if curr_idx - 1 >= 0 else gal_size - 1

			Instagram.__cache[key]['curr'] = curr_idx

			msg.embeds[0].set_image(url=Instagram.__cache[key]['images'][curr_idx])
			msg.embeds[0].set_field_at(1, name='Page', value=f"{Instagram.__cache[key]['curr'] + 1}/{len(Instagram.__cache[key]['images'])}")

			await msg.edit(embed=msg.embeds[0])
			await msg.remove_reaction(event.emoji, event.member)
