import re
from urllib.parse import parse_qs, urlparse

import discord
from discord.ext import commands

from cogs.instagram import Instagram
from cogs.reddit import Reddit
from db import BotDB


class Starboard(commands.Cog):
	__exceptions = dict()

	__bot: commands.Bot = None
	def __init__(self, bot):
		Starboard.__bot = bot

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, event: discord.RawReactionActionEvent):
		if not BotDB.is_setup(event.guild_id):
			return

		archive_emote = BotDB.find_server(event.guild_id)['archive_emote']
		if str(event.emoji) != archive_emote:
			return

		if BotDB.in_ignore_list(event.guild_id, event.channel_id, event.message_id):
			return

		msg = await (await Starboard.__bot.fetch_channel(event.channel_id)).fetch_message(event.message_id)

		if match := list(filter(lambda r: str(r.emoji) == archive_emote, msg.reactions)):
			custom_count = BotDB.get_custom_count(event.guild_id, event.channel_id)
			if match[0].count >= (custom_count['amount'] if custom_count else BotDB.find_server(event.guild_id)['archive_emote_amount']):
				await Starboard.do_archival(msg)

	@commands.command(brief = 'Removes the replied to message from the archive.')
	async def remove(self, ctx: commands.Context):
		if ctx.message.reference is None or not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please use the reply functionality.')
			return

		BotDB.conn['ignore_list'].delete(server_id = ctx.guild.id, channel_id = ctx.channel.id, message_id = ctx.message.reference.message_id)

	@commands.command(brief = 'Overrides the replied to message with a given direct link.')
	async def override(self, ctx: commands.Context, link: str):
		if ctx.message.reference is None or not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please use the reply functionality.')
			return

		Starboard.__exceptions[str(ctx.guild.id) + str(ctx.channel.id) + str(ctx.message.reference.message_id)] = link

		await ctx.message.delete()

	@commands.command(brief = 'Forces any given message into the archive.')
	async def force(self, ctx: commands.Context):
		if ctx.message.reference is None or not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please use the reply functionality.')
			return

		fetched = await ctx.fetch_message(ctx.message.reference.message_id)
		fetched.guild = ctx.guild

		await Starboard.do_archival(fetched)

	@commands.command(aliases = ['sch'], brief = 'Sets the archive channel.')
	async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel):
		if not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please set the bot up first.')
			return

		BotDB.conn['server'].update(dict(server_id = ctx.guild.id, archive_channel = channel.id), ['server_id'])
		await ctx.send(f'Set archive channel to <#{BotDB.find_server(ctx.guild.id)["archive_channel"]}>')

	@commands.command(aliases = ['sam'], brief = 'Sets the reaction amount requirement.')
	async def set_amount(self, ctx: commands.Context, value: int):
		if not BotDB.is_setup(ctx.guild.id):
			ctx.send('Please set the bot up first.')
			return

		BotDB.conn['server'].update(dict(server_id = ctx.guild.id, archive_emote_amount = value), ['server_id'])
		await ctx.send(f'Set necessary amount of {BotDB.find_server(ctx.guild.id)["archive_emote"]} to {BotDB.find_server(ctx.guild.id)["archive_emote_amount"]}')

	@commands.command(aliases=['scham'], brief = 'Sets the reaction amount requirement for a channel.')
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

		def set_info(flag='message', content=msg.content, media_url='', author=msg.author):
			info['flag'] = flag
			info['content'] = content
			info['media_url'] = media_url
			info['author'] = author

		set_info()

		if f'{msg.guild.id}{msg.channel.id}{msg.id}' in Starboard.__exceptions:
			set_info(
				'image',
				msg.content,
				Starboard.__exceptions.pop(f'{msg.guild.id}{msg.channel.id}{msg.id}'),
			)
		else:
			url = re.findall(r"https?://[\w\d_.~\-!*'();:@&=+$,/?#[\]]*", msg.content)
			# url without < > and no attachments
			if url and msg.embeds and not msg.attachments:
				if re.findall(r'https?://(?:v|f)xtwitter\.com/[a-zA-Z0-9_]+/status/\d+', url[0]):
					if msg.embeds[0].video:
						media_url = msg.embeds[0].video.url
					elif msg.embeds[0].thumbnail:
						media_url = msg.embeds[0].thumbnail.url

					def get_id():
						if quer_v := parse_qs(urlparse(url[0]).query).get('u'):
							return quer_v[0]

					set_info(
						'video' if msg.embeds[0].video else 'image',
						# fxtwitter puts likes, retweets, etc in the author field
						f'[{msg.embeds[0].title}]({url[0]})\n{msg.embeds[0].description}\n{msg.embeds[0].author.name if "fxtwitter" in url[0] else ""}',
						media_url,
						msg.author if not get_id() else await Starboard.__bot.fetch_user(get_id())
					)
				elif re.findall(r'https?://(?:www\.)?youtu(?:be.com/watch\?v=|\.be/)[A-Za-z0-9_\-]{11}', url[0]):
					def get_id():
						# handles normal urls
						if quer_v := parse_qs(urlparse(url[0]).query).get('v'):
							return quer_v[0]
						#handles short urls
						elif pth := url[0].split('youtu.be/'):
							return pth[1][0:11]

					set_info(
						'image',
						f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
						f'https://img.youtube.com/vi/{get_id()}/0.jpg',
					)
				elif any(ext in url[0] for ext in ['.mp4', '.mov', '.webm']):
					set_info(
						'video',
						f'[A video](https://youtu.be/dQw4w9WgXcQ)\n{msg.content.replace(url[0], "").strip()}',
						url[0],
					)
				else:
					# handles: tumblr, deviantart, imgur, tenor and many other things
					if msg.embeds[0].thumbnail:
						# ?u= in proxy links (twitter and pixiv)
						def get_id():
							if quer_v := parse_qs(urlparse(url[0]).query).get('u'):
								return quer_v[0]

						image_url = msg.embeds[0].thumbnail.url
						if re.findall(r'https?://(?:i\.)?imgur.com/(?:gallery/.+|.+\..+)', url[0]):
							# has to be proxy to work
							image_url = msg.embeds[0].thumbnail.proxy_url
						elif re.findall(r'https?://tenor\.com/view/.+', url[0]):
							# if we change .png to .gif and edit the 39th character to be d
							# we'll get a working .gif link
							image_url = list(msg.embeds[0].thumbnail.url)
							image_url[39] = 'd' # d yields the best quality gif
							image_url = ''.join(image_url).replace('.png', '.gif')

						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							image_url,
							msg.author if not get_id() else await Starboard.__bot.fetch_user(get_id())
						)
					# most embeds have a thumbnail with the image, but some don't and thus:
					elif msg.embeds[0].image:
						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							msg.embeds[0].image.url,
						)
			else:
				if msg.attachments:
					is_video = any(ext in msg.attachments[0].url.lower() for ext in ['.mp4', '.mov', '.webm'])
					is_spoiler = msg.attachments[0].is_spoiler()

					content = msg.content
					if is_video:
						if is_spoiler:
							content = f'[A video spoiler]({msg.attachments[0].url})\n{msg.content}'
						else:
							content = f'[A video](https://youtu.be/dQw4w9WgXcQ)\n{msg.content}'

					media_url = msg.attachments[0].url
					if is_spoiler:
						media_url = 'https://i.imgur.com/GFn7HTJ.png'

					set_info(
						'video' if is_video and not is_spoiler else 'image',
						content,
						media_url
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

		embed.set_author(name=embed_info["author"].name, icon_url=embed_info["author"].avatar.url)

		if embed_info['content']:
			embed.add_field(name='What?', value=embed_info['content'][0:1024], inline=False)

		embed.add_field(name='Where?', value=f'[Jump to ](https://discordapp.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id})<#{msg.channel.id}>')

		if embed_info['flag'] == 'image' and embed_info['media_url']:
			embed.set_image(url=embed_info['media_url'])

		embed.set_footer(text='by @roguezilla')

		await (await Starboard.__bot.fetch_channel(BotDB.find_server(msg.guild.id)['archive_channel'])).send(embed=embed)

		if embed_info['flag'] == 'video' and embed_info['media_url']:
			await (await Starboard.__bot.fetch_channel(BotDB.find_server(msg.guild.id)['archive_channel'])).send(embed_info['media_url'])

		BotDB.conn['ignore_list'].insert(dict(server_id = str(msg.guild.id), channel_id = str(msg.channel.id), message_id = str(msg.id)))
