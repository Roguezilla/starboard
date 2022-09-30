import re
from urllib.parse import parse_qs, urlparse

import perms
import requests
from bs4 import BeautifulSoup
from dataset import Database
from discpy.discpy import DiscPy
from discpy.events import ReactionAddEvent
from discpy.message import Embed, Message

from .reddit import Reddit
from cogs.instagram import Instagram

class Starboard(DiscPy.Cog):
	def __init__(self, bot: DiscPy, db: Database):
		@bot.event(self)
		async def on_reaction_add(event: ReactionAddEvent):
			if query_servers(event.guild_id) is None:
				return

			if str(event.emoji) != query_servers(event.guild_id)['archive_emote']:
				return

			if query_ignore_list(event.guild_id, event.channel_id, event.message_id) is not None:
				return

			msg: Message = await bot.fetch_message(event.channel_id, event.message_id)
			# because discord api was made by monkeys
			msg.guild_id = event.guild_id

			reaction_match = list(filter(lambda r: str(r.emoji) == query_servers(event.guild_id)['archive_emote'], msg.reactions))
			if reaction_match:
				channel_count = query_custom_counts(event.guild_id, event.channel_id)
				needed_count = channel_count['amount'] if channel_count is not None else query_servers(event.guild_id)['archive_emote_amount']
				# the message object can return the wrong reaction count for whatever reason(in this case, the value it returns is 1)
				# so we just make a "manual" calculation for the amount of reactions in that case
				# when reactions >100, fetch_emoji_count returns 100 (can be fixed with an interator using the after query field)
				if (await bot.fetch_emoji_count(msg, reaction_match[0]) if reaction_match[0].count == 1 else reaction_match[0].count) >= int(needed_count):
					await do_archival(bot, msg)
					

		@bot.command(self)
		@bot.permissions(perms.is_mod)
		async def remove(msg: Message):
			if msg.message_reference is None or query_servers(msg.guild_id) is None:
				return

			db['ignore_list'].delete(server_id = msg.guild_id, channel_id = msg.channel_id, message_id = msg.message_reference.message_id)

		@bot.command(self)
		@bot.permissions(perms.is_mod)
		async def override(msg: Message, link: str):
			if msg.message_reference is None or query_servers(msg.guild_id) is None:
				return

			exceptions[str(msg.guild_id) + str(msg.channel_id) + str(msg.message_reference.message_id)] = link
	
			await bot.delete_message(msg)

		@bot.command(self)
		@bot.permissions(perms.is_mod)
		async def force(msg: Message):
			if msg.message_reference:
				target = await bot.fetch_message(msg.channel_id, msg.message_reference.message_id)
				target.guild_id = msg.guild_id
				await do_archival(self, target)

		@bot.command(self)
		@bot.permissions(perms.is_mod)
		async def set_channel(msg: Message, value: str):
			if query_servers(msg.guild_id) is None:
				return
				
			db['server'].update(dict(server_id=str(msg.guild_id), archive_channel=value.strip('<>#')), ['server_id'])
			await bot.send_message(msg.channel_id, f'Set channel to <#{query_servers(msg.guild_id)["archive_channel"]}>')

		@bot.command(self)
		@bot.permissions(perms.is_mod)
		async def set_amount(msg: Message, value: int):
			if query_servers(msg.guild_id) is None:
				return
				
			db['server'].update(dict(server_id=str(msg.guild_id), archive_emote_amount=value), ['server_id'])
			await bot.send_message(msg.channel_id, 
				f'Set necessary amount of {query_servers(msg.guild_id)["archive_emote"]} '
				+ f'{query_servers(msg.guild_id)["archive_emote_amount"]}'
			)

		@bot.command(self)
		@bot.permissions(perms.is_mod)
		async def set_channel_amount(msg: Message, channel: str, value: int):
			if query_servers(msg.guild_id) is None:
				return

			if query_custom_counts(msg.guild_id, channel.strip('<>#')) is None:
				db['custom_count'].insert(dict(server_id = msg.guild_id, channel_id = channel.strip('<>#'), amount = value))
			else:
				db['custom_count'].update(dict(server_id = msg.guild_id, channel_id = channel.strip('<>#'), amount = value), ['server_id', 'channel_id'])
				
			await bot.send_message(msg.channel_id,
				f'Set necessary amount of {query_servers(msg.guild_id)["archive_emote"]} in '
				+ f'<#{query_custom_counts(msg.guild_id, channel.strip("<>#"))["channel_id"]}> to '
				+ f'{query_custom_counts(msg.guild_id, channel.strip("<>#"))["amount"]}'
			)

		exceptions = dict()

		def query_servers(id):
			return db['server'].find_one(server_id = id)

		def query_ignore_list(server_id, channel_id, msg_id):
			return db['ignore_list'].find_one(server_id = server_id, channel_id = channel_id, message_id = msg_id)

		def query_custom_counts(server_id, channel_id):
			return db['custom_count'].find_one(server_id = server_id, channel_id = channel_id)
		
		async def build_info(bot: DiscPy, msg: Message):
			info = {}

			def set_info(flag='message', content=msg.content, image_url='', custom_author=None):
				info['flag'] = flag
				info['content'] = content
				info['image_url'] = image_url
				info['custom_author'] = custom_author

			set_info()

			if f'{msg.guild_id}{msg.channel_id}{msg.id}' in exceptions:
				set_info(
					'image',
					msg.content,
					exceptions.pop(f'{msg.guild_id}{msg.channel_id}{msg.id}')
				)
			else:
				url = re.findall(r"((?:https?):(?://)+(?:[\w\d_.~\-!*'();:@&=+$,/?#[\]]*))", msg.content)
				# url without < > and no attachments
				if url and msg.embeds and not msg.attachments:
					if 'deviantart.com' in url[0] or 'tumblr.com' in url[0]:
						processed_url = requests.get(url[0].replace('mobile.', '')).text
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
								msg.author if not get_id() else await bot.fetch_user(get_id())
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
						# i actually do not remember why this check in partical is needed, but apparently the past me found some cases that needed
						# and it should be above the second condition
						if msg.embeds[0].url != url[0]:
							set_info(
								'image',
								f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
								msg.embeds[0].url
							)
						# """fallback""", """ because in 99% of cases this is going to be the condition that's hit
						elif msg.embeds[0].thumbnail:
							# ?u= in pixiv proxy links
							def get_id():
								if quer_v := parse_qs(urlparse(url[0]).query).get('u'):
									return quer_v[0]

							set_info(
								'image',
								f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
								msg.embeds[0].thumbnail.url,
								msg.author if not get_id() else await bot.fetch_user(get_id())
							)
						# instagram falls into this condition
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
							f'{msg.content}\n[{"Video spoiler alert!" if is_video else "Spoiler alert!"}]({msg.attachments[0].url})' if msg.attachments[0].is_spoiler
								else (f'[The video below](https://youtu.be/dQw4w9WgXcQ)\n{msg.content}' if is_video else msg.content),
							'' if msg.attachments[0].is_spoiler else msg.attachments[0].url
						)
					else:
						if Reddit.validate_embed(msg.embeds):
							content = msg.embeds[0].description.split('\n')
							set_info(
								'image',
								'\n'.join(content[1:]) if len(content) > 1 else '',
								msg.embeds[0].image.url,
								# unholy
								await bot.fetch_user(msg.embeds[0].fields[0].__dict__['value'][(3 if '!' in msg.embeds[0].fields[0].__dict__['value'] else 2):len(msg.embeds[0].fields[0].__dict__['value'])-1])
							)
						elif Instagram.validate_embed(msg.embeds):
							content = msg.embeds[0].description.split('\n')
							set_info(
								'image',
								'\n'.join(content[1:]) if len(content) > 1 else '',
								msg.embeds[0].image.url,
								# unholy
								await bot.fetch_user(msg.embeds[0].fields[0].__dict__['value'][(3 if '!' in msg.embeds[0].fields[0].__dict__['value'] else 2):len(msg.embeds[0].fields[0].__dict__['value'])-1])
							)

			return info

		async def do_archival(bot: DiscPy, msg: Message):
			embed_info = await build_info(bot, msg)
			if not embed_info:
				return

			embed = Embed(color = 0xffcc00)

			if embed_info['custom_author']:
				embed.set_author(name=f'{embed_info["custom_author"].username}', icon_url=f'{embed_info["custom_author"].avatar_url}')
			else:
				embed.set_author(name=f'{msg.author.username}', icon_url=f'{msg.author.avatar_url}')
			
			if embed_info['content']:
				embed.add_field(name='What?', value=embed_info['content'][0:1024], inline=False)

			embed.add_field(name='Where?', value=f'[Jump to ](https://discordapp.com/channels/{msg.guild_id}/{msg.channel_id}/{msg.id})<#{msg.channel_id}>')

			if embed_info['flag'] == 'image' and embed_info['image_url']:
				embed.set_image(url=embed_info['image_url'])

			embed.set_footer(text='by rogue#0001')

			await bot.send_message(query_servers(msg.guild_id)['archive_channel'], embed=embed.as_json())

			if embed_info['flag'] == 'video' and embed_info['image_url']:
				await bot.send_message(query_servers(msg.guild_id)['archive_channel'], embed_info['image_url'])

			db['ignore_list'].insert(dict(server_id = msg.guild_id, channel_id = msg.channel_id, message_id = msg.id))
