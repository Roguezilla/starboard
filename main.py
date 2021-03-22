import os
import re
import json
from urllib.parse import parse_qs, urlparse

import discord
import dataset
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
from requests_oauthlib import OAuth1

from instagram import Instagram
from reddit import Reddit
import perms

settings = dataset.connect('sqlite:///settings.db')
ignore_list = dataset.connect('sqlite:///ignore_list.db')

bot = commands.Bot(command_prefix='<>')

twitter = OAuth1(settings['twitter'].find_one(name='api_key')['value'], settings['twitter'].find_one(name='api_secret')['value'],
					settings['twitter'].find_one(name='access_token')['value'], settings['twitter'].find_one(name='access_token_secret')['value'])
exceptions = dict()

# https://stackoverflow.com/a/45579374
def get_id(url):
	u_pars = urlparse(url)
	quer_v = parse_qs(u_pars.query).get('v')
	if quer_v:
		return quer_v[0]
	pth = u_pars.path.split('/')
	if pth:
		return pth[-1]


@bot.event
async def on_ready():
	print(f'Logged in as {bot.user.name}')

	await bot.change_presence(activity=discord.Game(name='with stars'))

"""
info = {
	'flag'
	'content'
	'image_url'
	'custom_author'
}
"""
async def build_info(msg: discord.Message):
	info = {}

	def set_info(flag='', content='', image_url='', custom_author=''):
		info['flag'] = flag
		info['content'] = content
		info['image_url'] = image_url
		info['custom_author'] = custom_author

	# good ol' regex
	url = re.findall(
	    r"((?:https?):(?://)+(?:[\w\d_.~\-!*'();:@&=+$,/?#[\]]*))", msg.content)

	if str(msg.channel.id) + str(msg.id) in exceptions:
		set_info(
			'image',
			msg.content,
			exceptions.pop(str(msg.channel.id) + str(msg.id))
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
			elif 'www.instagram.com' in url[0] or 'redd.it' in url[0]:
				set_info(
					'image',
					f'[Source]({url[0]})\n{msg.content.replace(url[0], "").strip()}',
					Instagram.return_link(url[0])
				)
			elif 'twitter.com' in url[0]:
				# fuck twitter
				tweet_id = re.findall(r'https://twitter\.com/.*?/status/(\d*)', url[0].replace('mobile.', ''))
				r = json.loads(requests.get(f'https://api.twitter.com/1.1/statuses/show.json?id={tweet_id[0]}&tweet_mode=extended', auth=twitter).text)
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
					Reddit.return_link(url[0])
				)
			elif 'youtube.com' in url[0] or 'youtu.be' in url[0]:
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
					f'{msg.content}\n[{"Video spoiler alert!" if is_video else "Spoiler alert!"}]({msg.attachments[0].url})' if file.is_spoiler()
						else (f'[The video below](https://youtu.be/dQw4w9WgXcQ)\n{msg.content}' if is_video else msg.content),
					'' if file.is_spoiler() else msg.attachments[0].url
				)
			else:
				if msg.embeds:
					if any(x in msg.embeds[0].description for x in ['instagram.com', 'reddit.com', 'redd.it']):
						content = msg.embeds[0].description.split('\n')
						set_info(
							'image',
							'\n'.join(content[1:]) if len(content) > 1 else '',
							msg.embeds[0].image.__getattribute__('url'),
							await bot.fetch_user(int(msg.embeds[0].fields[0].__dict__['value'][2:len(msg.embeds[0].fields[0].__dict__['value'])-1]))
						)
				else:
					set_info(
						'message',
						msg.content,
					)

	return info

async def do_archival(msg: discord.Message):
	embed_info = await build_info(msg)
	if not embed_info:
		return

	embed = discord.Embed(color=0xffcc00)

	if embed_info['custom_author']:
		embed.set_author(name=f'{embed_info["custom_author"].display_name}', icon_url=f'{embed_info["custom_author"].avatar_url}')
	else:
		embed.set_author(name=f'{msg.author.display_name}', icon_url=f'{msg.author.avatar_url}')
	
	if embed_info['content']:
		embed.add_field(name='What?', value=embed_info['content'], inline=False)

	embed.add_field(name='Where?', value=msg.channel.mention, inline=True)
	embed.add_field(name='Where exactly?', value=f'[Jump!](https://discordapp.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id})', inline=True)

	if embed_info['flag'] == 'image' and embed_info['image_url']:
		embed.set_image(url=embed_info['image_url'])

	embed.set_footer(text="by rogue#0001")


	await bot.get_channel(int(settings[str(msg.guild.id)].find_one(name='archive_channel')['value'])).send(embed=embed)

	if embed_info['flag'] == 'video':
		await bot.get_channel(int(settings[str(msg.guild.id)].find_one(name='archive_channel')['value'])).send(embed_info['image_url'])

	ignore_list[str(msg.guild.id)].insert(dict(msgid=str(msg.channel.id) + str(msg.id)))

"""
on_raw_reaction_add is better than on_reaction_add in this case, because on_reaction_add only works with cached messages(the ones sent after the bot started).
"""
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
	# ignore the event if the bot isn't setup in the server
	if str(payload.guild_id) not in settings:
		return

	msg: discord.Message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

	if ignore_list[str(msg.guild.id)].find_one(msgid=str(msg.channel.id) + str(msg.id)) is not None:
		return

	emote_match = [reaction for reaction in msg.reactions if str(reaction) == settings[str(msg.guild.id)].find_one(name='archive_emote')['value']]
	if emote_match and emote_match[0].count >= int(settings[str(msg.guild.id)].find_one(name='archive_emote_amount')['value']):
		await do_archival(msg)
	
"""
Setups the bot.
"""
@bot.command(brief = 'Setups the bot for the server.')
@perms.mod()
async def setup(ctx: commands.Context, archive_channel: discord.TextChannel, archive_emote: discord.Emoji, archive_emote_amount: int):
	if str(ctx.guild.id) in settings:
		await ctx.send('Bot has been setup already.')
		return
	
	settings[str(ctx.guild.id)].insert(dict(name='archive_emote', value=str(archive_emote)))
	settings[str(ctx.guild.id)].insert(dict(name='archive_emote_amount', value=archive_emote_amount))
	settings[str(ctx.guild.id)].insert(dict(name='archive_channel', value=archive_channel.id))
	settings[str(ctx.guild.id)].insert(dict(name='reddit_embed', value=True))
	settings[str(ctx.guild.id)].insert(dict(name='instagram_embed', value=True))

"""
Sends the github link of the bot.
"""
@bot.command(brief = 'Links the github page of the bot.')
async def source(ctx: commands.Context):
	await bot.get_channel(ctx.message.channel.id).send('https://github.com/Roguezilla/starboard')

@bot.command(brief = 'Removes the given message from the archive cache.')
@perms.mod()
async def del_entry(ctx: commands.Context, msglink):
	if str(ctx.guild.id) not in settings:
		return

	"""
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""
	for type in ['https://discord.com/channels/', 'https://canary.discordapp.com/channels/', 'https://discordapp.com/channels/']:
		if type in msglink:
			msglink = msglink.replace(type, '')
	
	msg_data = msglink.split('/')

	ignore_list[str(ctx.guild.id)].delete(msgid=msg_data[1]+msg_data[2])

@bot.command(brief = 'Overrides archive images before archival.')
@perms.mod()
async def override(ctx: commands.Context, msglink, link):
	if str(ctx.guild.id) not in settings:
		return

	"""
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""
	for type in ['https://discord.com/channels/', 'https://canary.discordapp.com/channels/', 'https://discordapp.com/channels/']:
		if type in msglink:
			msglink = msglink.replace(type, '')
	
	msg_data = msglink.split('/')

	if msg_data[1] + msg_data[2] not in exceptions:
		exceptions[msg_data[1] + msg_data[2]] = link
	
	await ctx.message.delete()

@bot.command(brief = 'Used for reloading embeds.')
@perms.mod()
async def reload_embed(ctx: commands.Context, msglink):
	if str(ctx.guild.id) not in settings:
		return

	"""
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""
	msg_data = msglink.replace('https://canary.discordapp.com/channels/' if 'canary' in msglink else 'https://discordapp.com/channels/', '').split('/')

	msg: discord.Message = await bot.get_channel(int(msg_data[1])).fetch_message(int(msg_data[2]))
	embed: discord.Embed = msg.embeds[0]
	channel_id = msg.channel.id
	await msg.delete()
	await bot.get_channel(channel_id).send(embed=embed)


@bot.command(brief = 'Restarts the bot.')
@perms.owner()
async def restart(ctx: commands.Context):
	try:
		await bot.close()
	except:
		pass
	finally:
		os.system('python main.py')

bot.add_cog(Reddit(bot, settings))
bot.add_cog(Instagram(bot, settings))
bot.run(settings['settings'].find_one(name='token')['value'])
