import re
from typing import List

import discord
import requests
from discord.ext import commands
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from db import BotDB

# TODO: rewrite using web scrapping because the reddit api is getting paywall locked

"""
'msgid': {
	'curr': 0,
	'images': []
}
"""
class Reddit(commands.Cog):
	__cache = dict()

	__session = requests.Session()
	__session.mount('https://', HTTPAdapter(max_retries=Retry(
		total=10,
		status_forcelist=[429],
		respect_retry_after_header=True
	)))

	__regex = r'^https?://(?:www\.reddit.com/r/.+/comments/[0-9a-z]+(?:/.+)?|redd.it/[0-9a-z]+)$'

	def __init__(self, bot):
		self.bot: commands.Bot = bot

	@staticmethod
	def __build_cache(data, msg: discord.Message, repopulate=False):
		Reddit.__cache[str(msg.channel.id) + str(msg.id)] = {
			'curr': 0,
			'images': []
		}

		for i in range(len(data['gallery_data']['items'])):
			media_id = data['gallery_data']['items'][i]['media_id']
			Reddit.__cache[str(msg.channel.id) + str(msg.id)]['images'].append(data['media_metadata'][media_id]['s']['u'].replace('&amp;', '&'))

		# when repopulating, we need to match the current picture with its index
		if repopulate:
			for i in range(len(Reddit.__cache[str(msg.channel.id) + str(msg.id)]['images'])):
				if Reddit.__cache[str(msg.channel.id)+str(msg.id)]['images'][i] == msg.embeds[0].image.url:
					Reddit.__cache[str(msg.channel.id)+str(msg.id)]['curr'] = i

	@staticmethod
	def __url_data(url):
		# handle redirects and cut out useless stuff
		if 'redd.it' in url: url = Reddit.__session.head(url, allow_redirects=True).url
		else: url = url.split("?")[0]

		return Reddit.__session.get(url + '.json', headers = {'User-agent': 'RogueStarboard v1.0'}).json()[0]['data']['children'][0]['data']

	@staticmethod
	def get_data(url, msg):
		data = Reddit.__url_data(url)
		# only galeries have media_metadata
		if 'media_metadata' in data:
			# media_metadata is unordered, gallery_data has the right order
			first = data['gallery_data']['items'][0]['media_id']
			# the highest quality pic always the last one
			ret = data['media_metadata'][first]['s']['u'].replace('&amp;', '&')
			# as the link is a gallery, we need to populate the gallery cache
			Reddit.__build_cache(data, msg)
		else:
			# covers gifs
			ret = data['url_overridden_by_dest']
			# the url doesn't end with any of these then the post is a video, so fallback to the thumbnail
			if '.jpg' not in ret and '.png' not in ret and '.gif' not in ret:
				ret = data['preview']['images'][0]['source']['url'].replace('&amp;', '&')

		return (ret, data['title'])

	@commands.Cog.listener()
	async def on_message(self, event: discord.Message):
		if not BotDB.is_setup(event.guild.id) or event.author.bot:
			return

		if link := re.findall(Reddit.__regex, event.content):
			if data := Reddit.get_data(link[0], msg=event):
				embed = discord.Embed(color=0xffcc00, title=data[1], url=link[0])
				embed.set_image(url=data[0])
				embed.add_field(name='Original Poster', value=event.author.mention)

				sent = await event.channel.send(embed=embed)

				if str(event.channel.id) + str(event.id) in Reddit.__cache:
					key = str(sent.channel.id) + str(sent.id)
					# copy original message cache into the new message(our embed) and delete the original message from the cache
					Reddit.__cache[key] = Reddit.__cache[str(event.channel.id) + str(event.id)]
					del Reddit.__cache[str(event.channel.id) + str(event.id)]

					sent.embeds[0].add_field(name='Page', value=f"{Reddit.__cache[key]['curr'] + 1}/{len(Reddit.__cache[key]['images'])}")
					await sent.edit(embed=sent.embeds[0])

					await sent.add_reaction('⬅️')
					await sent.add_reaction('➡️')

				# we don't really the message and it only occupies space now
				await event.delete()

	@staticmethod
	def validate_embed(embeds: List[discord.Embed]) -> bool:
		if not embeds: return False
		if not re.findall(Reddit.__regex, embeds[0].url): return False
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
		if key not in Reddit.__cache:
			Reddit.__build_cache(Reddit.__url_data(msg.embeds[0].url), msg, True)

		if key in Reddit.__cache:
			gal_size = len(Reddit.__cache[key]['images'])
			curr_idx = Reddit.__cache[key]['curr']

			if str(event.emoji) == '➡️':
				curr_idx = curr_idx + 1 if curr_idx + 1 < gal_size else 0
			else:
				curr_idx = curr_idx - 1 if curr_idx - 1 >= 0 else gal_size - 1

			Reddit.__cache[key]['curr'] = curr_idx

			msg.embeds[0].set_image(url=Reddit.__cache[key]['images'][curr_idx])
			msg.embeds[0].set_field_at(1, name='Page', value=f"{Reddit.__cache[key]['curr'] + 1}/{len(Reddit.__cache[key]['images'])}")

			await msg.edit(embed=msg.embeds[0])
			await msg.remove_reaction(event.emoji, event.member)
