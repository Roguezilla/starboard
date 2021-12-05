import re
from urllib.parse import parse_qs, urlparse

import perms
import requests
from bs4 import BeautifulSoup
from dataset import Database
from discpy.discpy import DiscPy
from discpy.events import ReactionAddEvent
from discpy.message import Embed, Message
from requests_oauthlib import OAuth1


class Starboard(DiscPy.Cog):
	def __init__(self, bot: DiscPy, db: Database):
		@bot.event(self)
		async def on_reaction_add(ctx: DiscPy, event: ReactionAddEvent):
			if query_servers(event.guild_id) is None:
				return

			try:
				msg: Message = await ctx.fetch_message(event.channel_id, event.message_id)
				# becaused discord api was made by monkeys
				msg.guild_id = event.guild_id
			except:
				return

			if query_ignore_list(event.guild_id, event.channel_id, event.message_id) is not None:
				return

			for reaction in msg.reactions:
				if str(reaction.emoji) == query_servers(event.guild_id)['archive_emote']:
					channel_count = query_custom_counts(event.guild_id, event.channel_id)
					needed_count = channel_count['amount'] if channel_count is not None else query_servers(event.guild_id)['archive_emote_amount']
					if int(reaction.count) >= int(needed_count):
						await do_archival(msg)

		@bot.command()
		@bot.permissions(perms.is_mod)
		async def del_entry(self: DiscPy, msg: Message, msg_id: str):
			if query_servers(msg.guild_id) is None:
				return

			db['ignore_list'].delete(server_id = msg.guild_id, channel_id = msg.channel_id, message_id = msg_id)

		@bot.command()
		@bot.permissions(perms.is_mod)
		async def override(self: DiscPy, msg: Message, msg_id: str, link):
			if query_servers(msg.guild_id) is None:
				return

			exceptions[str(msg.guild_id) + str(msg.channel_id) + msg_id] = link
	
			await self.delete_message(msg)

		@bot.command()
		@bot.permissions(perms.is_mod)
		async def set_channel(self: DiscPy, msg: Message, value: str):
			if query_servers(msg.guild_id) is None:
				return
				
			db['server'].update(dict(server_id=str(msg.guild_id), archive_channel=value.strip('<>#')), ['server_id'])
			await self.send_message(msg.channel_id, f'Set channel to <#{query_servers(msg.guild_id)["archive_channel"]}>')

		@bot.command()
		@bot.permissions(perms.is_mod)
		async def set_amount(self: DiscPy, msg: Message, value: int):
			if query_servers(msg.guild_id) is None:
				return
				
			db['server'].update(dict(server_id=str(msg.guild_id), archive_emote_amount=value), ['server_id'])
			await self.send_message(msg.channel_id, 
				f'Set necessary amount of {query_servers(msg.guild_id)["archive_emote"]} '
				+ f'{query_servers(msg.guild_id)["archive_emote_amount"]}'
			)

		@bot.command()
		@bot.permissions(perms.is_mod)
		async def set_channel_amount(self: DiscPy, msg: Message, channel: str, value: int):
			if query_servers(msg.guild_id) is None:
				return

			if query_custom_counts(msg.guild_id, channel.strip('<>#')) is None:
				db['custom_count'].insert(dict(server_id = msg.guild_id, channel_id = channel.strip('<>#'), amount = value))
			else:
				db['custom_count'].update(dict(server_id = msg.guild_id, channel_id = channel.strip('<>#'), amount = value), ['server_id', 'channel_id'])
				
			await self.send_message(msg.channel_id,
				f'Set necessary amount of {query_servers(msg.guild_id)["archive_emote"]} in '
				+ f'<#{query_custom_counts(msg.guild_id, channel.strip("<>#"))["channel_id"]}> to '
				+ f'{query_custom_counts(msg.guild_id, channel.strip("<>#"))["amount"]}'
			)
				
		twitter = OAuth1(
			db['twitter'].find_one(name='api_key')['value'],
			db['twitter'].find_one(name='api_secret')['value'],
			db['twitter'].find_one(name='access_token')['value'],
			db['twitter'].find_one(name='access_token_secret')['value']
		)

		exceptions = dict()

		def query_servers(id):
			return db['server'].find_one(server_id = id)

		def query_ignore_list(server_id, channel_id, msg_id):
			return db['ignore_list'].find_one(server_id = server_id, channel_id = channel_id, message_id = msg_id)

		def query_custom_counts(server_id, channel_id):
			return db['custom_count'].find_one(server_id = server_id, channel_id = channel_id)
		
		async def build_info(msg: Message):
			info = {}

			def set_info(flag='', content='', image_url='', custom_author=''):
				info['flag'] = flag
				info['content'] = content
				info['image_url'] = image_url
				info['custom_author'] = custom_author

			# good ol' regex
			url = re.findall(
				r"((?:https?):(?://)+(?:[\w\d_.~\-!*'();:@&=+$,/?#[\]]*))", msg.content)

			if f'{msg.guild_id}{msg.channel_id}{msg.id}' in exceptions:
				set_info(
					'image',
					msg.content,
					exceptions.pop(f'{msg.guild_id}{msg.channel_id}{msg.id}')
				)
			else:
				# tldr, someone might want to override the image
				if url and not msg.attachments:
					if 'deviantart.com' in url[0] or 'tumblr.com' in url[0] or 'pixiv.net' in url[0]:
						processed_url = requests.get(url[0].replace('mobile.', '')).text
						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							BeautifulSoup(processed_url, 'html.parser').find('meta', attrs={'property': 'og:image'}).get('content')
						)
					elif 'www.instagram.com' in url[0]:
						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							'Instagram.return_link(url[0])'
						)
					elif 'twitter.com' in url[0]:
						# fuck twitter
						tweet_id = re.findall(r'https://twitter\.com/.*?/status/(\d*)', url[0].replace('mobile.', ''))
						r = requests.get(f'https://api.twitter.com/1.1/statuses/show.json?id={tweet_id[0]}&tweet_mode=extended', auth=twitter).json()
						if 'errors' not in r:
							if 'media' in r['entities']:
								set_info(
									'image',
									f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
									r['entities']['media'][0]['media_url']
								)	
							else:
								set_info(
									'message',
									msg.content
								)
					elif 'reddit.com' in url[0] or 'redd.it' in url[0]:
						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							'Reddit.return_link(url[0])[0]'
						)
					elif 'youtube.com' in url[0] or 'youtu.be' in url[0]:
						def get_id(url):
							u_pars = urlparse(url)
							quer_v = parse_qs(u_pars.query).get('v')
							if quer_v:
								return quer_v[0]
							pth = u_pars.path.split('/')
							if pth:
								return pth[-1]
						
						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							f'https://img.youtube.com/vi/{get_id(url[0])}/0.jpg'
						)
					elif 'dcinside.com' in url[0]:
						set_info(
							'image',
							f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
							msg.attachments[0].url
						)
					elif 'imgur' in url[0]:
						if 'i.imgur' not in url[0]:
							processed_url = requests.get(url[0].replace('mobile.', '')).text
							set_info(
								'image',
								f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
								BeautifulSoup(processed_url, 'html.parser').find('meta', attrs={'property': 'og:image'}).get('content').replace('?fb', '')
							)
						else:
							set_info(
								'image',
								msg.content.replace(url[0], "").strip(),
								url[0]
							)
					elif 'https://tenor.com' in url[0]:
						processed_url = requests.get(url[0].replace('mobile.', '')).text
						for img in BeautifulSoup(processed_url, 'html.parser').findAll('img', attrs={'src': True}):
							if 'media1.tenor.com' in img.get('src'):
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
					elif 'discordapp.com' in url[0] or 'twimg.com' in url[0]:
						set_info(
							'image',
							msg.content.replace(url[0], '').strip(),
							msg.embeds[0].url
						)
					else:
						# high chance that it's the actual image
						if msg.embeds and msg.embeds[0].url != url[0]:
							set_info(
								'image',
								f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
								msg.embeds[0].url
							)
						else:
							set_info(
								'message',
								msg.content,
							)
				else:
					if msg.attachments:
						file = msg.attachments[0]
						is_video = any(ext in msg.attachments[0].url for ext in ['.mp4', '.mov', '.webm'])
						set_info(
							'video' if is_video else 'image',
							f'{msg.content}\n[{"Video spoiler alert!" if is_video else "Spoiler alert!"}]({msg.attachments[0].url})' if file.is_spoiler
								else (f'[The video below](https://youtu.be/dQw4w9WgXcQ)\n{msg.content}' if is_video else msg.content),
							'' if file.is_spoiler else msg.attachments[0].url
						)
					else:
						if 'Reddit.validate_embed(msg.embeds) or Instagram.validate_embed(msg.embeds)' and False:
							content = msg.embeds[0].description.split('\n')
							set_info(
								'image',
								'\n'.join(content[1:]) if len(content) > 1 else '',
								msg.embeds[0].image.__getattribute__('url'),
								await bot.fetch_user(msg.embeds[0].fields[0].__dict__['value'][(3 if '!' in msg.embeds[0].fields[0].__dict__['value'] else 2):len(msg.embeds[0].fields[0].__dict__['value'])-1])
							)
						else:
							set_info(
								'message',
								msg.content,
							)

			return info

		async def do_archival(msg: Message):
			embed_info = await build_info(msg)
			if not embed_info:
				return

			embed = Embed(color = 0xffcc00)

			if embed_info['custom_author']:
				embed.set_author(name=f'{embed_info["custom_author"].username}', icon_url=f'{embed_info["custom_author"].username}')
			else:
				embed.set_author(name=f'{msg.author.username}', icon_url=f'{msg.author.avatar_url}')
			
			if embed_info['content']:
				embed.add_field(name='What?', value=embed_info['content'], inline=False)

			embed.add_field(name='Where?', value=f'<#{msg.channel_id}>', inline=True)
			embed.add_field(name='Where exactly?', value=f'[Jump!](https://discordapp.com/channels/{msg.guild_id}/{msg.channel_id}/{msg.id})', inline=True)

			if embed_info['flag'] == 'image' and embed_info['image_url']:
				embed.set_image(url=embed_info['image_url'])

			embed.set_footer(text="by rogue#0001")

			await bot.send_message(query_servers(msg.guild_id)['archive_channel'], embed=embed.as_json())

			if embed_info['flag'] == 'video':
				await bot.send_message(query_servers(msg.guild_id)['archive_channel'], embed_info['image_url'])

			db['ignore_list'].insert(dict(server_id = msg.guild_id, channel_id = msg.channel_id, message_id = msg.id))
