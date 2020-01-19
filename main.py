import json
import os
import re
import sys
import traceback
import urllib.request
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import discord
from bs4 import BeautifulSoup
from discord.ext import commands

cfg = json.load(open('bot.json'))

# https://stackoverflow.com/a/45579374
def get_id(url):
    u_pars = urlparse(url)
    quer_v = parse_qs(u_pars.query).get('v')
    if quer_v:
        return quer_v[0]
    pth = u_pars.path.split('/')
    if pth:
        return pth[-1]

async def buildEmbed(msg, url):
    embed = discord.Embed()

    if len(msg.content):
        embed.add_field(name='Content', value=msg.content, inline=False)
    embed.add_field(name='Message Link', value='https://discordapp.com/channels/{}/{}/{}'.format(
        msg.guild.id, msg.channel.id, msg.id), inline=False)
    embed.add_field(name='Author', value=msg.author.mention, inline=True)
    embed.add_field(name='Channel', value=msg.channel.mention, inline=True)
    embed.set_image(url=url)

    await bot.get_channel(cfg['bot']['archive_channel']).send(embed=embed)

bot = commands.Bot(command_prefix='<>')


@bot.event
async def on_ready():
    print('Logged in as {}'.format(bot.user.name))

    if not os.path.exists('.git'):
        os.system('git init')
        os.system('git remote add origin https://github.com/Roguezilla/starboard.git')

    await bot.change_presence(activity=discord.Game(name='with stars'))


@bot.event
async def on_raw_reaction_add(payload):
    try:
        msg = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

        if msg.created_at > datetime(2019, 11, 19, 1, 0, 0, 723674):
            if str(payload.channel_id+payload.message_id) not in cfg['ignore_list']:
                for reaction in msg.reactions:
                    if str(reaction) == cfg['bot']['archive_emote']:
                        url = re.findall(
                            r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', msg.content)
                        if url:
                            if ('dcinside.com' in url[0][0] and not msg.attachments) or ('pixiv.net' in url[0][0] and not msg.attachments):
                                await bot.get_channel(payload.channel_id).send('https://discordapp.com/channels/{}/{}/{} not supported, please attach the image that you want to archive to the link.'.format(msg.guild.id, msg.channel.id, msg.id))

                                cfg['ignore_list'][str(payload.channel_id+payload.message_id)] = 1
                                json.dump(cfg, open('bot.json', 'w'), indent=4)
                        if reaction.count >= cfg['bot']['archive_emote_amount']:
                            if str(payload.channel_id+payload.message_id) in cfg['exceptions']:
                                await buildEmbed(msg, cfg['exceptions'][str(payload.channel_id+payload.message_id)])

                                del cfg['exceptions'][str(
                                    payload.channel_id+payload.message_id)]
                                json.dump(cfg, open('bot.json', 'w'), indent=4)
                            else:
                                if url:
                                    processed_url = ''
                                    if 'https://cdn.discordapp.com/' not in url[0][0]:
                                        processed_url = urllib.request.urlopen(url[0][0]).read().decode('utf-8', 'ignore')
                                    if 'deviantart.com' in url[0][0] or 'twitter.com' in url[0][0] or 'www.instagram.com' in url[0][0] or 'www.tumblr.com' in url[0][0]:
                                        for tag in BeautifulSoup(processed_url, 'html.parser').findAll('meta'):
                                            if tag.get('property') == 'og:image':
                                                await buildEmbed(msg, tag.get('content'))
                                                break
                                    elif 'youtube.com' in url[0][0] or 'youtu.be' in url[0][0]:
                                        await buildEmbed(msg, 'https://img.youtube.com/vi/{}/0.jpg'.format(get_id(url[0][0])))
                                    elif 'dcinside.com' in url[0][0] or 'pixiv.net' in url[0][0]:
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

                            cfg['ignore_list'][str(payload.channel_id+payload.message_id)] = 1
                            json.dump(cfg, open('bot.json', 'w'), indent=4)
    except:
        if str(payload.channel_id+payload.message_id) not in cfg['ignore_list']:
            await bot.get_user(cfg['bot']['owner_id']).send('https://discordapp.com/channels/{}/{}/{}\n'.format(msg.guild.id, msg.channel.id, msg.id) + '```python\n' + traceback.format_exc() + '\n```')
            cfg['ignore_list'][str(payload.channel_id+payload.message_id)] = 1
            json.dump(cfg, open('bot.json', 'w'), indent=4)


@bot.command()
async def run(ctx, *args):
    if ctx.message.author.id != cfg['bot']['owner_id']:
        return

    await bot.get_user(cfg['bot']['owner_id']).send(eval(' '.join(args)))


@bot.command()
async def exc(ctx, msglink, link):
    if ctx.message.author.id != cfg['bot']['owner_id']:
        return

    msg_data = msglink.replace('https://discordapp.com/channels/', '').split('/')
    """
	msg_data[0] -> server id
	msg_data[1] -> channel id
	msg_data[2] -> msg id
	"""

    if str(int(msg_data[1]) + int(msg_data[2])) not in cfg['exceptions']:
        cfg['exceptions'][str(int(msg_data[1]) + int(msg_data[2]))] = link
        json.dump(cfg, open('bot.json', 'w'), indent=4)


@bot.command()
async def update(ctx):
    if ctx.message.author.id != cfg['bot']['owner_id']:
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

bot.run(cfg['bot']['token'])
