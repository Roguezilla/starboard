import json
import os
import re
from urllib.parse import parse_qs, urlparse

def sr():
	start_reqs()

def start_reqs():
	print("")
	print("Failed to find one more more requirements, would you like to automatically install them?")
	print("(Requires pip3 to be installed on the system.)")
	x = input("Y/n: ")
	if str.lower(x) == "n":
		print("Bot can't start without requirements, have a nice day!")
		exit()
	else:
		os.system("pip3 install -r requirements.txt")

def sc():
	start_config()

def start_config():
	print("")
	print("Failed to find config file, would you like to create one?")
	x = input("Y/n: ")
	if str.lower(x) == "n":
		print("Boot can't start without config, have a nice day!")
		exit()
	else:
		print("")
		print("Bot Token:")
		id = input("> ")
		temp = {"token" : id}
		json.dump(temp, open('bot.json', 'w'), indent=4)
		temp = 0

try:
	import discord
	from discord.ext import commands
	from bs4 import BeautifulSoup
	import requests
except:
	sr()

if os.path.isfile("bot.json"):
	cfg = json.load(open('bot.json'))
else:
	sc()
	cfg = json.load(open('bot.json'))



exceptions = []

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
async def buildEmbed(msg, url, tweet = ''):
	embed = discord.Embed()

	if len(tweet):
		embed.add_field(name='Tweet content', value=tweet, inline=False)
	elif isinstance(msg, discord.Message) and len(msg.content):
		embed.add_field(name='Content', value=msg.content, inline=False)
	embed.add_field(name='Message Link', value='https://discordapp.com/channels/{}/{}/{}'.format(msg.guild.id, msg.channel.id, msg.id), inline=False)
	embed.add_field(name='Author', value=msg.author.mention, inline=True)
	embed.add_field(name='Channel', value=msg.channel.mention, inline=True)
	embed.set_image(url=url)

	await bot.get_channel(cfg[str(msg.guild.id)]['bot']['archive_channel']).send(embed=embed)

bot = commands.Bot(command_prefix='<>')

@bot.event
async def on_ready():
	print('Logged in as {}'.format(bot.user.name))

	await bot.change_presence(activity=discord.Game(name='with stars'))

"""
I use on_raw_reaction_add instead of on_reaction_add, because on_reaction_add doesn't work with messages that were sent before the bot went online.
"""
@bot.event
async def on_raw_reaction_add(payload):
	msg = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

	if str(msg.guild.id) not in cfg:
		await bot.get_channel(payload.channel_id).send("Please set up the bot with <>setup archive_channel archive_emote archive_emote_amount.")
		return

	msg_id = str(payload.channel_id)+str(payload.message_id)

	if msg_id in cfg[str(msg.guild.id)]['ignore_list']:
		return

	for reaction in msg.reactions:
		if str(reaction) == cfg[str(msg.guild.id)]['bot']['archive_emote']:
			url = re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', msg.content)
			if url:
				if 'dcinside.com' in url[0][0] and not msg.attachments:
					await bot.get_channel(payload.channel_id).send('https://discordapp.com/channels/{}/{}/{} not supported, please attach the image that you want to archive to the link.'.format(msg.guild.id, msg.channel.id, msg.id))

					cfg[str(msg.guild.id)]['ignore_list'].append(msg_id)
					json.dump(cfg, open('bot.json', 'w'), indent=4)
					return
			if reaction.count >= cfg[str(msg.guild.id)]['bot']['archive_emote_amount']:
				if msg_id in exceptions:
					await buildEmbed(msg, exceptions[msg_id])

					exceptions.remove(msg_id)
					json.dump(cfg, open('bot.json', 'w'), indent=4)
				else:
					if url:
						processed_url = requests.get(url[0][0].replace('mobile.', '')).text
						# gotta strip off the url from msg.conent cuz we dont really need to see it do we?
						msg.content = msg.content.replace(url[0][0], '').replace('<>', '').strip()
						"""
						most sites that can host images, put the main image into the og:image property, so we get the links to the images from there
						<meta property="og:image" content="link" />
						"""
						if 'deviantart.com' in url[0][0] or 'www.instagram.com' in url[0][0] or 'tumblr.com' in url[0][0] or 'pixiv.net' in url[0][0]:
							await buildEmbed(msg, BeautifulSoup(processed_url, 'html.parser').find('meta', attrs={'property':'og:image'}).get('content'))
						elif 'twitter.com' in url[0][0]:
							"""
							either archive the image in the tweet if there is one or archive the text
							"""
							for tag in BeautifulSoup(processed_url, 'html.parser').findAll('meta'):
								if tag.get('property') == 'og:image' and 'profile_images' not in tag.get('content'):
									await buildEmbed(msg, tag.get('content'))
									break
								elif tag.get('property') == 'og:description':
									await buildEmbed(msg, '', tag.get('content'))
									break
						elif 'youtube.com' in url[0][0] or 'youtu.be' in url[0][0]:
							await buildEmbed(msg, 'https://img.youtube.com/vi/{}/0.jpg'.format(get_id(url[0][0])))
						elif 'dcinside.com' in url[0][0]:
							await buildEmbed(msg, msg.attachments[0].url)
						elif 'imgur' in url[0][0]:
							if 'i.imgur' not in url[0][0]:
								await buildEmbed(msg, BeautifulSoup(processed_url, 'html.parser').find('meta', attrs={'property':'og:image'}).get('content').replace('?fb', ''))
							else:
								await buildEmbed(msg, url[0][0])
						elif 'https://tenor.com' in url[0][0]:
							for img in BeautifulSoup(processed_url, 'html.parser').findAll('img', attrs={'src': True}):
								if 'media1.tenor.com' in img.get('src'):
									await buildEmbed(msg, img.get('src'))
						else:
							if msg.embeds and msg.embeds[0].url != url[0][0]:
								await buildEmbed(msg, msg.embeds[0].url)
							else:
								if msg.attachments:
									await buildEmbed(msg, msg.attachments[0].url)
								else:
									await buildEmbed(msg, '')
					else:
						if msg.attachments:
							await buildEmbed(msg, msg.attachments[0].url)
						else:
							await buildEmbed(msg, '')

				cfg[str(msg.guild.id)]['ignore_list'].append(msg_id)
				json.dump(cfg, open('bot.json', 'w'), indent=4)

"""
Used to setup the bot.
"""
@bot.command(brief='Sets up the bot.')
@commands.has_permissions(administrator=True)
async def setup(ctx, archive_channel: discord.TextChannel, archive_emote: discord.Emoji, archive_emote_amount: int):
	if str(ctx.guild.id) in cfg:
		return
	
	cfg[str(ctx.guild.id)] = {
		'ignore_list': [],
		'bot': {
			'archive_channel': archive_channel.id,
			'archive_emote': str(archive_emote),
			'archive_emote_amount': archive_emote_amount,
		}
	}
	json.dump(cfg, open('bot.json', 'w'), indent=4)


"""
Deletes the given message from archive cache.
"""
@bot.command(brief='Removes the given message from the archive cache.')
@commands.has_permissions(administrator=True)
async def del_entry(ctx, msglink: str):
	if str(ctx.guild.id) not in cfg:
		await ctx.send("Please set up the bot with <>setup archive_channel archive_emote archive_emote_amount.")
		return

	msg_data = msglink.replace('https://canary.discordapp.com/channels/' if 'canary' in msglink else 'https://discordapp.com/channels/', '').split('/')
	"""
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""

	cfg[ctx.guild.id]['ignore_list'].remove(msg_data[1]+msg_data[2])
	json.dump(cfg, open('bot.json', 'w'), indent=4)


"""
Overrides the image that was going to the archived originally.
"""
@bot.command(brief='Overrides the image that was going to the archived originally.')
@commands.has_permissions(administrator=True)
async def override(ctx, msglink: str, link: str):
	if str(ctx.guild.id) not in cfg:
		await ctx.send("Please set up the bot with <>setup archive_channel archive_emote archive_emote_amount.")
		return
		
	msg_data = msglink.replace('https://canary.discordapp.com/channels/' if 'canary' in msglink else 'https://discordapp.com/channels/', '').split('/')
	"""
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""

	if msg_data[1] + msg_data[2] not in exceptions:
		exceptions.append(msg_data[1] + msg_data[2])

bot.run(cfg['token'])
