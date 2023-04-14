import re
from urllib.parse import parse_qs, urlparse

import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from cogs.instagram import Instagram
from cogs.reddit import Reddit
from db import BotDB


class Starboard(commands.Cog):
	__exceptions = dict()

	__session = requests.Session()
	__session.mount('https://', HTTPAdapter(max_retries=Retry(
		total=10,
		status_forcelist=[429],
		method_whitelist=None,
		respect_retry_after_header=True
	)))

	__bot: commands.Bot = None
	def __init__(self, bot):
		Starboard.__bot = bot

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, event: discord.RawReactionActionEvent):
		if not BotDB.is_setup(event.guild_id):
			return
		
		if str(event.emoji) != BotDB.find_server(event.guild_id)['archive_emote']:
			return

		if BotDB.in_ignore_list(event.guild_id, event.channel_id, event.message_id) is not None:
			return
		
		msg = await (await Starboard.__bot.fetch_channel(event.channel_id)).fetch_message(event.message_id)
		msg.guild.id = event.guild_id

		match = list(filter(lambda r: str(r.emoji) == BotDB.find_server(event.guild_id)['archive_emote'], msg.reactions))
		if match:
			cc = BotDB.get_custom_count(event.guild_id, event.channel_id)
			needed = cc['amount'] if cc is not None else BotDB.find_server(event.guild_id)['archive_emote_amount']
			if match[0].count >= needed: await Starboard.do_archival(msg)

	@commands.command()
	async def remove(self, ctx: commands.Context):
		if ctx.message.reference is None or not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please use the reply functionality.')
			return

		BotDB.conn['ignore_list'].delete(server_id = ctx.guild.id, channel_id = ctx.channel.id, message_id = ctx.message.reference.message_id)

	@commands.command()
	async def override(self, ctx: commands.Context, link: str):
		if ctx.message.reference is None or not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please use the reply functionality.')
			return
		
		Starboard.__exceptions[str(ctx.guild.id) + str(ctx.channel.id) + str(ctx.message.reference.message_id)] = link
	
		await ctx.message.delete()

	@commands.command()
	async def force(self, ctx: commands.Context):
		if ctx.message.reference is None or not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please use the reply functionality.')
			return
		
		fetched = await ctx.fetch_message(ctx.message.reference.message_id)
		fetched.guild = ctx.guild
		
		await Starboard.do_archival(fetched)

	@commands.command(aliases=['sch'])
	async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel):
		if not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please set the bot up first.')
			return
		
		BotDB.conn['server'].update(dict(server_id = ctx.guild.id, archive_channel = channel.id), ['server_id'])
		await ctx.send(f'Set channel to <#{BotDB.find_server(ctx.guild.id)["archive_channel"]}>')

	@commands.command(aliases=['sam'])
	async def set_amount(self, ctx: commands.Context, value: int):
		if not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please set the bot up first.')
			return
		
		BotDB.conn['server'].update(dict(server_id = ctx.guild.id, archive_emote_amount = value), ['server_id'])
		await ctx.send( 
			f'Set necessary amount of {BotDB.find_server(ctx.guild.id)["archive_emote"]} '
			+ f'{BotDB.find_server(ctx.guild.id)["archive_emote_amount"]}'
		)

	@commands.command(aliases=['scham'])
	async def set_channel_amount(self, ctx: commands.Context, channel: discord.TextChannel, value: int):
		if not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please set the bot up first.')
			return
		
		if BotDB.get_custom_count(ctx.guild.id, channel.id) is None:
			BotDB.conn['custom_count'].insert(dict(server_id = ctx.guild.id, channel_id = channel.id, amount = value))
		else:
			BotDB.conn['custom_count'].update(dict(server_id = ctx.guild.id, channel_id = channel.id, amount = value), ['server_id', 'channel_id'])

		await ctx.send(
			f'Set necessary amount of {BotDB.find_server(ctx.guild.id)["archive_emote"]} in '
			+ f'<#{BotDB.get_custom_count(ctx.guild.id, channel.id)["channel_id"]}> to '
			+ f'{BotDB.get_custom_count(ctx.guild.id, channel.id)["amount"]}'
		)

	@staticmethod
	async def __build_info(msg: discord.Message):
		info = dict()

		def set_info(flag='message', content=msg.content, image_url='', custom_author=None):
			info['flag'] = flag
			info['content'] = content
			info['image_url'] = image_url
			info['custom_author'] = custom_author

		set_info()

		if f'{msg.guild.id}{msg.channel.id}{msg.id}' in Starboard.__exceptions:
			set_info(
				'image',
				msg.content,
				Starboard.__exceptions.pop(f'{msg.guild.id}{msg.channel.id}{msg.id}')
			)
		else:
			url = re.findall(r"((?:https?):(?://)+(?:[\w\d_.~\-!*'();:@&=+$,/?#[\]]*))", msg.content)
			# url without < > and no attachments
			if url and msg.embeds and not msg.attachments:
				if 'deviantart.com' in url[0] or 'tumblr.com' in url[0]:
					processed_url = Starboard.__session.get(url[0].replace('mobile.', '')).text
					set_info(
						'image',
						f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
						BeautifulSoup(processed_url, 'html.parser').find('meta', attrs={'property': 'og:image'}).get('content')
					)
				elif 'twitter.com' in url[0]:
					if tweet_data := re.findall(r'https://(?:mobile.)?(vx)?twitter\.com/.+/status/\d+(?:/photo/(\d+))?', url[0])[0]:
						content_url = ''
						if tweet_data[0] and msg.embeds[0].video:
							content_url = msg.embeds[0].video.url
						elif msg.embeds[0].image:
							content_url = msg.embeds[0 if tweet_data[1] == '' else max(0, min(int(tweet_data[1]) - 1, 4))].image.url
						
						def get_id():
							if quer_v := parse_qs(urlparse(url[0]).query).get('u'):
								return quer_v[0]

						content = f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}'
						if not content_url:
							content = f'[Tweet by]({url[0]})\n**{msg.embeds[0].author.name}**\n\n{msg.embeds[0].description}'

						set_info(
							'video' if msg.embeds[0].video else 'image',
							content,
							content_url,
							msg.author if not get_id() else await Starboard.__bot.fetch_user(get_id())
						)
				elif 'youtube.com' in url[0] or 'youtu.be' in url[0]:
					def get_id():
						parse_result = urlparse(url[0])
						# handles normal urls
						if quer_v := parse_qs(parse_result.query).get('v'):
							return quer_v[0]
						#handles short urls
						elif pth := parse_result.path.split('/'):
							return pth[-1]
					
					set_info(
						'image',
						f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
						f'https://img.youtube.com/vi/{get_id()}/0.jpg'
					)
				elif 'imgur' in url[0]:
					if 'i.imgur' not in url[0]:
						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							BeautifulSoup(requests.get(url[0].replace('mobile.', '')).text, 'html.parser').find('meta', attrs={'property': 'og:image'}).get('content').replace('?fb', '')
						)
					else:
						set_info(
							'image',
							msg.content.replace(url[0], "").strip(),
							url[0]
						)
				elif 'https://tenor.com' in url[0]:
					bs = BeautifulSoup(requests.get(url[0].replace('mobile.', '')).text, 'html.parser')

					for img in bs.find_all('img', attrs={'src': True}):
						if 'c.tenor.com' in img.get('src') and img.get('alt').startswith(bs.find('h1').contents[0]):
							set_info(
								'image',
								f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
								img.get('src')
							)
				elif any(ext in url[0] for ext in ['.mp4', '.mov', '.webm']):
					set_info(
						'video',
						f'[The video below](https://youtu.be/dQw4w9WgXcQ)\n{msg.content.replace(url[0], "").strip()}',
						url[0]
					)
				else:
					# i actually do not remember why this is here but apparently it's necessary in some cases
					if msg.embeds[0].url != url[0]:
						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							msg.embeds[0].url
						)
					# 99% of cases this is going to be the condition that's hit instead of the one above
					elif msg.embeds[0].thumbnail:
						# ?u= in pixiv proxy links
						def get_id():
							if quer_v := parse_qs(urlparse(url[0]).query).get('u'):
								return quer_v[0]

						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							msg.embeds[0].thumbnail.url,
							msg.author if not get_id() else await Starboard.__bot.fetch_user(get_id())
						)
					# thing like instagram falls into this condition
					elif msg.embeds[0].image:
						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							msg.embeds[0].image.url
						)
			else:
				if msg.attachments:
					is_video = any(ext in msg.attachments[0].url for ext in ['.mp4', '.mov', '.webm'])
					set_info(
						'video' if is_video else 'image',
						f'{msg.content}\n[{"Video spoiler alert!" if is_video else "Spoiler alert!"}]({msg.attachments[0].url})' if msg.attachments[0].is_spoiler()
							else (f'[The video below](https://youtu.be/dQw4w9WgXcQ)\n{msg.content}' if is_video else msg.content),
						'' if msg.attachments[0].is_spoiler() else msg.attachments[0].url
					)
				else:
					if Reddit.validate_embed(msg.embeds) or Instagram.validate_embed(msg.embeds):
						set_info(
							'image',
							"",
							msg.embeds[0].image.url,
							await Starboard.__bot.fetch_user(msg.embeds[0].fields[0].value[2:len(msg.embeds[0].fields[0].value)-1])
						)

		return info

	@staticmethod
	async def do_archival(msg: discord.Message):
		embed_info = await Starboard.__build_info(msg)
		if not embed_info: return

		embed = discord.Embed(color = 0xffcc00)

		if embed_info['custom_author']:
			embed.set_author(name=f'{embed_info["custom_author"].name}', icon_url=f'{embed_info["custom_author"].avatar.url}')
		else:
			embed.set_author(name=f'{msg.author.name}', icon_url=f'{msg.author.avatar.url}')
		
		if embed_info['content']:
			embed.add_field(name='What?', value=embed_info['content'][0:1024], inline=False)

		embed.add_field(name='Where?', value=f'[Jump to ](https://discordapp.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id})<#{msg.channel.id}>')

		if embed_info['flag'] == 'image' and embed_info['image_url']:
			embed.set_image(url=embed_info['image_url'])

		embed.set_footer(text='by rogue#2001')

		await (await Starboard.__bot.fetch_channel(BotDB.find_server(msg.guild.id)['archive_channel'])).send(embed=embed)

		if embed_info['flag'] == 'video' and embed_info['image_url']:
			await (await Starboard.__bot.fetch_channel(BotDB.find_server(msg.guild.id)['archive_channel'])).send(embed_info['image_url'])

		BotDB.conn['ignore_list'].insert(dict(server_id = str(msg.guild.id), channel_id = str(msg.channel.id), message_id = str(msg.id)))
