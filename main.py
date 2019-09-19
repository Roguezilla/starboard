import discord
from discord.ext import commands
from bs4 import BeautifulSoup

import urllib.request
import re
import json
from datetime import datetime
import traceback
import os

BASE_TIME = datetime(2019, 9, 6, 9, 0, 0, 723674)
CHANNEL_ID = 497775435229167616
EMOJI = '<:LilyPad:544666310617858078>'
AMOUNT = 10

exceptions = dict()
ignores = dict()

async def buildEmbed(msg, url):
	embed = discord.Embed()
	if len(msg.content):
		embed.add_field(name='Content', value=msg.content, inline=False)
	else:
		pass
	embed.add_field(name='Message Link', value='https://discordapp.com/channels/{}/{}/{}'.format(msg.guild.id, msg.channel.id, msg.id), inline=False)
	embed.add_field(name='Author', value=msg.author.mention, inline=True)
	embed.add_field(name='Channel', value=msg.channel.mention, inline=True)
	embed.set_image(url=url)
	await bot.get_channel(CHANNEL_ID).send(embed=embed)  

bot = commands.Bot(command_prefix='<>')

@bot.event
async def on_ready():
	print('Logged in as {}'.format(bot.user.name))
	await bot.get_user(212149701535989760).send('E')

	exceptions.update(json.load(open('exceptions.json')))
	ignores.update(json.load(open('ignores.json')))

	os.system('git init')
	os.system('git remote add origin https://github.com/Roguezilla/starboard.git')

	await bot.change_presence(activity=discord.Game(name='with stars'))

@bot.event
async def on_raw_reaction_add(payload):
	try:
		msg = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
		
		if msg.created_at > BASE_TIME:
			if str(payload.channel_id+payload.message_id) not in ignores:
				for reaction in msg.reactions:
					if str(reaction) == EMOJI:
						url =  re.findall(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', msg.content)
						if url:
							if 'media.tumblr.com' not in url[0][0] and '.tumblr.com' in url[0][0]:
								await bot.get_channel(payload.channel_id).send('https://discordapp.com/channels/{}/{}/{} not supported, please use direct link to the picture instead.'.format(msg.guild.id, msg.channel.id, msg.id))
								ignores[str(payload.channel_id+payload.message_id)] = 1
								json.dump(ignores, open('ignores.json', 'w'))
						if reaction.count >= AMOUNT:
							if str(payload.channel_id+payload.message_id) in exceptions:
								await buildEmbed(msg, exceptions[str(payload.channel_id+payload.message_id)])

								del exceptions[str(payload.channel_id+payload.message_id)]
								json.dump(exceptions, open('exceptions.json', 'w'))
							else:
								if url:
									if 'deviantart.com' in url[0][0]:
										for img in BeautifulSoup(urllib.request.urlopen(url[0][0]).read().decode('utf-8'), 'html.parser').findAll('img', attrs={'src': True}):
											if 'images-wixmp' in img.get('src'):
												await buildEmbed(msg, img.get('src'))
												break
									elif 'twitter.com' in url[0][0]:
										for img in BeautifulSoup(urllib.request.urlopen(url[0][0]).read().decode('utf-8'), 'html.parser').findAll('img', attrs={'src': True}):
											if 'https://pbs.twimg.com/media/' in img.get('src'):
												await buildEmbed(msg, img.get('src'))
												break
									elif 'instagram.flis5-1.fna.fbcdn.net' in url[0][0]:
										await buildEmbed(msg, msg.embeds[0].url)
									elif 'cdninstagram.com' in url[0][0]:
										await buildEmbed(msg, msg.embeds[0].url)
									elif 'instagram.com' in url[0][0]:
										for tag in BeautifulSoup(urllib.request.urlopen(url[0][0]).read().decode('utf-8'), 'html.parser').findAll('meta'):
											if tag.get('property') == 'og:image':
												await buildEmbed(msg, tag.get('content'))
												break
									elif 'dcinside.com' in url[0][0]:
										try:
											await buildEmbed(msg, msg.attachments[0].url)
										except:
											await bot.get_channel(payload.channel_id).send('https://discordapp.com/channels/{}/{}/{} not supported, please attach the image that you want to be archived to the link.'.format(msg.guild.id, msg.channel.id, msg.id))
									elif 'pixiv.net' in url[0][0]:
										try:
											await buildEmbed(msg, msg.attachments[0].url)
										except:
											await bot.get_channel(payload.channel_id).send('https://discordapp.com/channels/{}/{}/{} not supported, please attach the image that you want to be archived to the link.'.format(msg.guild.id, msg.channel.id, msg.id))
									elif 'https://tenor.com' in url[0][0]:
										for img in BeautifulSoup(urllib.request.urlopen(url[0][0]).read().decode('utf-8'), 'html.parser').findAll('img', attrs={'src': True}):
											if 'media1.tenor.com' in img.get('src'):
												await buildEmbed(msg, img.get('src'))
									elif '.tumblr.com' not in url[0][0] or 'media.tumblr.com' in url[0][0]:
										await buildEmbed(msg, msg.embeds[0].url)
								else:
									if msg.attachments:
										await buildEmbed(msg, msg.attachments[0].url)
									else:
										await buildEmbed(msg, '')
									
							ignores[str(payload.channel_id+payload.message_id)] = 1
							json.dump(ignores, open('ignores.json', 'w'))
	except Exception as e:
		if str(payload.channel_id+payload.message_id) not in ignores:
			await bot.get_user(212149701535989760).send('https://discordapp.com/channels/{}/{}/{}'.format(msg.guild.id, msg.channel.id, msg.id))
			await bot.get_user(212149701535989760).send(e)
			await bot.get_user(212149701535989760).send('```python\n' + traceback.format_exc() + '\n```')
			ignores[str(payload.channel_id+payload.message_id)] = 1
			json.dump(ignores, open('ignores.json', 'w'))

@bot.command()
async def exception(ctx, msglink, link):
	if ctx.message.author.id != 212149701535989760:
		return

	channelid = re.findall(r'https://discordapp.com/channels/(.*?)/(.*?)/.*?', msglink)
	msgid = msglink.replace('https://discordapp.com/channels/{}/{}/'.format(channelid[0][0], channelid[0][1]), '')
	
	if str(int(msgid)+int(channelid[0][1])) not in exceptions:
		exceptions[str(int(msgid)+int(channelid[0][1]))] = link
		json.dump(exceptions, open('exceptions.json', 'w'))

@bot.command()
async def update(ctx):
	if ctx.message.author.id != 212149701535989760:
		return

	os.system('git fetch')
	os.system('git checkout origin/master main.py')
	await bot.get_channel(ctx.message.channel.id).send('Files updated.') 

	try:
		await bot.close()
	except:
		pass
	finally:
		os.system('python main.py')

bot.run(json.load(open('bot.json'))["token"])
