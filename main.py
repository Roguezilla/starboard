import json
import os
import re
import requests
from urllib.parse import parse_qs, urlparse

import discord
from bs4 import BeautifulSoup
from discord.ext import commands

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

async def buildEmbed(msg, url, custommsg = ''):
	embed = discord.Embed()

	if len(custommsg):
		embed.add_field(name='Tweet content', value=custommsg, inline=False)
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

	if str(payload.channel_id)+str(payload.message_id) in cfg[str(msg.guild.id)]['ignore_list']:
		return

	for reaction in msg.reactions:
		if str(reaction) == cfg[str(msg.guild.id)]['bot']['archive_emote']:
			url = re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', msg.content)
			if url:
				if 'dcinside.com' in url[0][0] and not msg.attachments:
					await bot.get_channel(payload.channel_id).send('https://discordapp.com/channels/{}/{}/{} not supported, please attach the image that you want to archive to the link.'.format(msg.guild.id, msg.channel.id, msg.id))

					cfg[str(msg.guild.id)]['ignore_list'].append(str(payload.channel_id)+str(payload.message_id))
					json.dump(cfg, open('bot.json', 'w'), indent=4)
					return
			if reaction.count >= cfg[str(msg.guild.id)]['bot']['archive_emote_amount']:
				if str(payload.channel_id)+str(payload.message_id) in exceptions:
					await buildEmbed(msg, exceptions[str(payload.channel_id)+str(payload.message_id)])

					exceptions.remove(str(payload.channel_id)+str(payload.message_id))
					json.dump(cfg, open('bot.json', 'w'), indent=4)
				else:
					if url:
						processed_url = requests.get(url[0][0].replace('mobile.', '')).text
						"""
						most sites that can host images, put the main imaga into the og:image property, so we get the links for the images from there
						<meta property="og:image" content="link" />
						"""
						if 'deviantart.com' in url[0][0] or 'www.instagram.com' in url[0][0] or 'www.tumblr.com' in url[0][0] or 'pixiv.net' in url[0][0]:
							for tag in BeautifulSoup(processed_url, 'html.parser').findAll('meta'):
								if tag.get('property') == 'og:image':
									await buildEmbed(msg, tag.get('content'))
									break
						elif 'twitter.com' in url[0][0]:
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
						elif 'https://tenor.com' in url[0][0]:
							for img in BeautifulSoup(processed_url, 'html.parser').findAll('img', attrs={'src': True}):
								if 'media1.tenor.com' in img.get('src'):
									await buildEmbed(msg, img.get('src'))
						else:
							await buildEmbed(msg, msg.embeds[0].url)
					else:
						if msg.attachments:
							await buildEmbed(msg, msg.attachments[0].url)
						else:
							await buildEmbed(msg, '')

				cfg[str(msg.guild.id)]['ignore_list'].append(str(payload.channel_id)+str(payload.message_id))
				json.dump(cfg, open('bot.json', 'w'), indent=4)

"""
Used to setup the bot.
"""
@bot.command()
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
Deletes an entry from cfg['ignore_list']
"""
@bot.command()
@commands.has_permissions(administrator=True)
async def del_entry(ctx, msglink):
	msg_data = msglink.replace('https://canary.discordapp.com/channels/' if 'canary' in msglink else 'https://discordapp.com/channels/', '').split('/')
	"""
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""

	cfg[ctx.guild.id]['ignore_list'].remove(msg_data[1]+msg_data[2])
	json.dump(cfg, open('bot.json', 'w'), indent=4)


"""
Overrides the original image that was going to the archived
"""
@bot.command()
@commands.has_permissions(administrator=True)
async def override(ctx, msglink, link):
	msg_data = msglink.replace('https://canary.discordapp.com/channels/' if 'canary' in msglink else 'https://discordapp.com/channels/', '').split('/')
	"""
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""

	if msg_data[1] + msg_data[2] not in exceptions:
		exceptions.append(msg_data[1] + msg_data[2])

@bot.command()
async def restart(ctx):
	if ctx.message.author.id != cfg['bot']['owner_id']:
		return
	
	try:
		await bot.close()
	except:
		pass
	finally:
		os.system('python main.py')

bot.run(cfg['token'])
