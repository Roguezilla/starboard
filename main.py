import os
import re
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

lockdown_mode = False

db = dataset.connect('sqlite:///db.db')

bot = commands.Bot(command_prefix  = 'sb!', owner_id = int(db['settings'].find_one(name='owner_id')['value']))

twitter = OAuth1(db['twitter'].find_one(name='api_key')['value'], db['twitter'].find_one(name='api_secret')['value'],
		 db['twitter'].find_one(name='access_token')['value'], db['twitter'].find_one(name='access_token_secret')['value'])
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

def get_server(id):
	return db['server'].find_one(server_id = id)

def get_ignore_list(id):
	return db['ignore_list'].find_one(server_id = id)

def get_custom_count(server_id, channel_id):
	return db['custom_count'].find_one(server_id= server_id, channel_id = channel_id)

@bot.event
async def on_ready():
	print(f'Logged in as {bot.user.name}')

	await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='the stars'))

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

	if f'{msg.guild.id}{msg.channel.id}{msg.id}' in exceptions:
		set_info(
			'image',
			msg.content,
			exceptions.pop(f'{msg.guild.id}{msg.channel.id}{msg.id}')
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
					Instagram.return_link(url[0])
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
					Reddit.return_link(url[0])[0]
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
				if Reddit.validate_embed(msg.embeds) or Instagram.validate_embed(msg.embeds):
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


	await bot.get_channel(int(get_server(msg.guild.id)['archive_channel'])).send(embed=embed)

	if embed_info['flag'] == 'video':
		await bot.get_channel(int(get_server(msg.guild.id)['archive_channel'])).send(embed_info['image_url'])

	db['ignore_list'].insert(dict(server_id = msg.guild.id, channel_id = msg.channel.id, message_id = msg.id))

"""
on_raw_reaction_add is better than on_reaction_add in this case, because on_reaction_add only works with cached messages(the ones sent after the bot started).
"""
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
	# ignore the event if the bot isn't setup in the server
	if get_server(payload.guild_id) is None or lockdown_mode:
		return

	try:
		msg: discord.Message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
	except:
		return

	if db['ignore_list'].find_one(server_id = payload.guild_id, channel_id = payload.channel_id, message_id = payload.message_id) is not None:
		return

	emote_match = list(filter(lambda r: str(r) == get_server(payload.guild_id)['archive_emote'], msg.reactions))
	channel_count = db['custom_count'].find_one(server_id = payload.guild_id, channel_id = payload.channel_id)
	needed_count = channel_count['amount'] if channel_count is not None else get_server(payload.guild_id)['archive_emote_amount']
	if emote_match and emote_match[0].count >= needed_count:
		await do_archival(msg)

"""
Setups the bot.
"""
@bot.command(brief = 'Setups the bot for the server.')
@perms.mod()
async def setup(ctx: commands.Context, archive_channel: discord.TextChannel, archive_emote, archive_emote_amount: int):
	if get_server(ctx.guild.id) is not None:
		await ctx.send('Bot has been setup already.')
		return
	
	db['server'].insert(dict(
		server_id = ctx.guild.id,
		archive_channel = archive_channel.id,
		archive_emote = str(archive_emote),
		archive_emote_amount = archive_emote_amount,
		reddit_embed = True,
		instagram_embed = True
	))

	await ctx.send('Done.')

@bot.command(brief='Debug')
@perms.owner()
async def eval_code(ctx: commands.Context, *args):
	await (await bot.fetch_user(bot.owner_id)).send(eval(' '.join(args)))

"""
Sends the github link of the bot.
"""
@bot.command(brief = 'Links the github page of the bot.')
async def source(ctx: commands.Context):
	await bot.get_channel(ctx.message.channel.id).send('https://github.com/Roguezilla/starboard')

@bot.command(brief = 'Removes the given message from the archive cache.')
@perms.mod()
async def del_entry(ctx: commands.Context, msg_id: str):
	if get_server(ctx.guild.id) is None:
		return

	db['ignore_list'].delete(server_id = ctx.guild.id, channel_id = ctx.channel.id, message_id = msg_id)

@bot.command(brief = 'Overrides archive images before archival.')
@perms.mod()
async def override(ctx: commands.Context, msg_id: str, link):
	if get_server(ctx.guild.id) is None:
		return

	exceptions[str(ctx.guild.id) + str(ctx.channel.id) + msg_id] = link
	
	await ctx.message.delete()

@bot.command(brief = 'Reloads embeds.')
@perms.mod()
async def reload(ctx: commands.Context, msg_id: int):
	if get_server(ctx.guild.id) is None:
		return

	channel: discord.TextChannel = bot.get_channel(int(get_server(ctx.guild.id)['archive_channel']))
	msg: discord.Message = await channel.fetch_message(msg_id)
	embed: discord.Embed = msg.embeds[0]
	await msg.delete()
	await channel.send(embed=embed)

@bot.command(brief='Sets the archive channel.', aliases=['sch'])
@perms.mod()
async def set_channel(ctx: commands.Context, value: discord.TextChannel):
	if get_server(ctx.guild.id) is None:
		return
		
	db['server'].update(dict(server_id=str(ctx.guild.id), archive_channel=value.id), ['server_id'])
	await ctx.channel.send('Set channel to ' + f'<#{bot.get_channel(get_server(ctx.guild.id)["archive_channel"]).id}>')

@bot.command(brief='Sets the amount of emotes necessary for archival.', aliases=['samt'])
@perms.mod()
async def set_amount(ctx: commands.Context, value: int):
	if get_server(ctx.guild.id) is None:
		return
		
	db['server'].update(dict(server_id=str(ctx.guild.id), archive_emote_amount=value), ['server_id'])
	await ctx.channel.send('Set necessary amount of ' + get_server(ctx.guild.id)['archive_emote'] + ' to ' + str(get_server(ctx.guild.id)['archive_emote_amount']))

@bot.command(brief='Sets the amount of emotes necessary for archival.', aliases=['scamt'])
@perms.mod()
async def set_channel_amount(ctx: commands.Context, channel: discord.TextChannel, value: int):
	if get_server(ctx.guild.id) is None:
		return

	if get_custom_count(ctx.guild.id, channel.id) is None:
		db['custom_count'].insert(dict(server_id = ctx.guild.id, channel_id = channel.id, amount = value))
	else:
		db['custom_count'].update(dict(server_id = ctx.guild.id, channel_id = channel.id, amount = value), ['server_id', 'channel_id'])
		
	await ctx.channel.send('Set necessary amount of ' + get_server(ctx.guild.id)['archive_emote'] + ' in ' + f'<#{get_custom_count(ctx.guild.id, channel.id)["channel_id"]}>' + ' to ' + str(get_custom_count(ctx.guild.id, channel.id)['amount']))

@bot.command(brief = 'Lockdown.')
@perms.owner()
async def lock(ctx: commands.Context, *reason: str):
	# TODO stick this into the db
	global lockdown_mode

	lockdown_mode = not lockdown_mode
	for server in db['server']:
		await bot.get_channel(server.get('archive_channel')).send('Lockdown mode ' + ('deactivated\n' if not lockdown_mode else 'activated.\n') + (('Reason:' + ' '.join(reason)) if len(reason) else ''))

@bot.command(brief = 'Restarts the bot.')
@perms.owner()
async def restart(ctx: commands.Context):
	await ctx.send('Restarting...')

	try:
		await bot.close()
	except:
		pass
	finally:
		os.system('python main.py')

bot.add_cog(Reddit(bot, db))
bot.add_cog(Instagram(bot, db))
bot.run(db['settings'].find_one(name='token')['value'])
