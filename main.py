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

db = None
if not os.path.exists('bot.db'):
	print('Welcome to starboard setup.')
	print('You will also need a twitter app, see https://developer.twitter.com/apps.')
	# create file if it doenst exist
	open('bot.db', 'w+').close()

	# connect to db and start setting up the bot
	db = dataset.connect('sqlite:///bot.db')

	print('Your bot\'s token can be obtained from https://discord.com/developers/applications.')
	token = input('Bot token: ')
	db['settings'].insert(dict(name='token', value=token))
	print('For this part you need to open the \'Keys and tokens\' tab of your twitter app.')
	api_key = input('API key: ')
	db['twitter'].insert(dict(name='api_key', value=api_key))
	api_secret = input('API secret key: ')
	db['twitter'].insert(dict(name='api_secret', value=api_secret))
	access_token = input('Access token: ')
	db['twitter'].insert(dict(name='access_token', value=access_token))
	access_token_secret = input('Access token secret: ')
	db['twitter'].insert(dict(name='access_token_secret', value=access_token_secret))

	print('All done, enjoy your starboard.\n')


bot = commands.Bot(command_prefix='<>')

if db is None:
	db = dataset.connect('sqlite:///bot.db')

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

"""
tweet is only used when we want to archive the text from a tweet
"""
async def send_embed(db, msg: discord.Message, url, tweet='', author=''):
	embed = discord.Embed()

	# custom content for embeding tweets with only text
	if len(tweet):
		embed.add_field(name='Tweet content', value=tweet, inline=False)
	# we need to check if the passed variable is an instance of discord.Message before 
	# checking the length, because 'msg: discord.Message' doesn't ensure that
	elif isinstance(msg, discord.Message) and len(msg.content):
		embed.add_field(name='Content', value=msg.content, inline=False)

	embed.add_field(name='Message Link', value='https://discordapp.com/channels/{}/{}/{}'.format(msg.guild.id, msg.channel.id, msg.id), inline=False)

	# custom author for when we embed embeds, see last lines of on_raw_reaction_add for example
	embed.add_field(name='Author', value=author if author else msg.author.mention, inline=True)
	
	embed.add_field(name='Channel', value=msg.channel.mention, inline=True)
	embed.set_image(url=url)

	embed.set_footer(text="by rogue#0001")

	await bot.get_channel(int(db.find_one(name='archive_channel')['value'])).send(embed=embed)
	# scuffed video support
	if any(ext in url for ext in ['.mp4', '.mov', '.webm']):
		await bot.get_channel(int(db.find_one(name='archive_channel')['value'])).send(url)

@bot.event
async def on_ready():
	print('Logged in as {}'.format(bot.user.name))

	await bot.change_presence(activity=discord.Game(name='with stars'))

"""
on_raw_reaction_add is better than on_reaction_add in this case, because on_reaction_add only works with cached messages(the ones sent after the bot started).
"""
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
	# ignore the event if the bot isn't setup in the server
	if str(payload.guild_id) not in db:
		return

	msg_id = str(payload.channel_id)+str(payload.message_id)
	msg: discord.Message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

	if db[str(msg.guild.id)].find_one(msgid=msg_id) is not None:
		return

	# is the reaction we are looking for in the list of message reactions?
	archive_emote = [reaction for reaction in msg.reactions if str(reaction) == db[str(msg.guild.id)].find_one(name='archive_emote')['value']]
	if archive_emote:
		# not sure where i found this one, iirc it was on stackoverflow
		url = re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', msg.content)
		if url:
			if 'dcinside.com' in url[0][0] and not msg.attachments:
				await bot.get_channel(payload.channel_id).send('https://discordapp.com/channels/{}/{}/{} not supported, please attach the image that you want to archive to the link.'.format(msg.guild.id, msg.channel.id, msg.id))
				
				db[str(msg.guild.id)].insert(dict(msgid=msg_id))
				return
		if archive_emote[0].count >= int(db[str(msg.guild.id)].find_one(name='archive_emote_amount')['value']):
			db[str(msg.guild.id)].insert(dict(msgid=msg_id))
			if msg_id in exceptions:
				await send_embed(msg, msg, exceptions.pop(msg_id))
			else:            
				if url and not msg.attachments:
					processed_url = requests.get(url[0][0].replace('mobile.', '')).text
					"""
					most sites that can host images, put the main image into the og:image property, so we get the links to the images from there
					<meta property="og:image" content="link" />
					"""
					if 'deviantart.com' in url[0][0] or 'tumblr.com' in url[0][0] or 'pixiv.net' in url[0][0]:
						await send_embed(db[str(msg.guild.id)], msg, BeautifulSoup(processed_url, 'html.parser').find('meta', attrs={'property':'og:image'}).get('content'))
					elif 'www.instagram.com' in url[0][0] or 'redd.it' in url[0][0]:
						await send_embed(db[str(msg.guild.id)], msg, Instagram.return_link(url[0][0]))
					elif 'twitter.com' in url[0][0]:
						# fuck twitter
						tweet_id = re.findall(r'https://twitter\.com/.*?/status/(\d*)', url[0][0].replace('mobile.', ''))
						r = json.loads(requests.get(f'https://api.twitter.com/1.1/statuses/show.json?id={tweet_id[0]}&tweet_mode=extended', auth=twitter).text)
						if 'media' in r['entities']:
							await send_embed(db[str(msg.guild.id)], msg, r['entities']['media'][0]['media_url'])
						else:
							await send_embed(db[str(msg.guild.id)], msg, '', r['full_text'])
					elif 'reddit.com' in url[0][0] or 'redd.it' in url[0][0]:
						await send_embed(db[str(msg.guild.id)], msg, Reddit.return_link(url[0][0]))
					elif 'youtube.com' in url[0][0] or 'youtu.be' in url[0][0]:
						await send_embed(db[str(msg.guild.id)], msg, f'https://img.youtube.com/vi/{get_id(url[0][0])}/0.jpg')
					elif 'dcinside.com' in url[0][0]:
						await send_embed(db[str(msg.guild.id)], msg, msg.attachments[0].url)
					elif 'imgur' in url[0][0]:
						if 'i.imgur' not in url[0][0]:
							await send_embed(db[str(msg.guild.id)], msg, BeautifulSoup(processed_url, 'html.parser').find('meta', attrs={'property': 'og:image'}).get('content').replace('?fb', ''))
						else:
							await send_embed(db[str(msg.guild.id)], msg, url[0][0])
					elif 'https://tenor.com' in url[0][0]:
						for img in BeautifulSoup(processed_url, 'html.parser').findAll('img', attrs={'src': True}):
							if 'media1.tenor.com' in img.get('src'):
								await send_embed(db[str(msg.guild.id)], msg, img.get('src'))
					elif 'discordapp.com' in url[0][0] or 'twimg.com' in url[0][0]:
						await send_embed(db[str(msg.guild.id)], msg, img.get('src'))
					elif 'discordapp.com' in url[0][0]:
						await send_embed(db[str(msg.guild.id)], msg, msg.embeds[0].url)
					else:
						if msg.embeds and msg.embeds[0].url != url[0][0]:
							await send_embed(db[str(msg.guild.id)], msg, msg.embeds[0].url)
						else:
							await send_embed(db[str(msg.guild.id)], msg, '')
				else:
					if msg.attachments:
						if msg.attachments[0].url:
							await send_embed(db[str(msg.guild.id)], msg, msg.attachments[0].url)
					else:
						if msg.embeds:
							if 'instagram.com' in msg.embeds[0].description:
								await send_embed(db[str(msg.guild.id)], msg, msg.embeds[0].image.__getattribute__('url'), author=msg.embeds[0].fields[0].__getattribute__('value'))
							elif 'reddit.com' in msg.embeds[0].description or 'redd.it' in msg.embeds[0].description:
								await send_embed(db[str(msg.guild.id)], msg, msg.embeds[0].image.__getattribute__('url'), author=msg.embeds[0].fields[0].__getattribute__('value'))
						else:
							await send_embed(db[str(msg.guild.id)], msg, '')

"""
Setups the bot.
"""
@bot.command(brief='Setups the bot for the server.')
@perms.mod()
async def setup(ctx: discord.ext.commands.Context, archive_channel: discord.TextChannel, archive_emote: discord.Emoji, archive_emote_amount: int):
	if str(ctx.guild.id) in db:
		ctx.send('Bot has been setup already.')
		return
	
	db[str(ctx.guild.id)].insert(dict(name='archive_emote', value=str(archive_emote)))
	db[str(ctx.guild.id)].insert(dict(name='archive_emote_amount', value=archive_emote_amount))
	db[str(ctx.guild.id)].insert(dict(name='archive_channel', value=archive_channel.id))
	db[str(ctx.guild.id)].insert(dict(name='reddit_embed', value=False))
	db[str(ctx.guild.id)].insert(dict(name='instagram_embed', value=True))

"""
Sends the github link of the bot.
"""
@bot.command(brief='Links the github page of the bot.')
async def source(ctx: discord.ext.commands.Context):
	await bot.get_channel(ctx.message.channel.id).send('https://github.com/Roguezilla/starboard')

"""
Deletes an entry from cfg['ignore_list']
"""
@bot.command(brief='Removes the given message from the archive cache.')
@perms.mod()
async def del_entry(ctx: discord.ext.commands.Context, msglink):
	if str(ctx.guild.id) not in db:
		return

	"""
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""
	msg_data = msglink.replace('https://canary.discordapp.com/channels/' if 'canary' in msglink else 'https://discordapp.com/channels/', '').split('/')

	db[str(ctx.guild.id)].delete(msgid=msg_data[1]+msg_data[2])

"""
Overrides the original image that was going to the archived
"""
@bot.command(brief='Overrides the image that was going to the archived originally.')
@perms.mod()
async def override(ctx: discord.ext.commands.Context, msglink, link):
	if str(ctx.guild.id) not in db:
		return

	"""
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""
	msg_data = msglink.replace('https://canary.discordapp.com/channels/' if 'canary' in msglink else 'https://discordapp.com/channels/', '').split('/')

	if msg_data[1] + msg_data[2] not in exceptions:
		exceptions[msg_data[1] + msg_data[2]] = link


@bot.command(brief='Restarts the bot.')
@perms.owner()
async def restart(ctx: discord.ext.commands.Context):
	try:
		await bot.close()
	except:
		pass
	finally:
		os.system('python main.py')

bot.add_cog(Reddit(bot, db))
bot.add_cog(Instagram(bot, db))
bot.run(db['settings'].find_one(name='token')['value'])
