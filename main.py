import subprocess as sp
import sys

import discord
from discord.ext import commands

import perms
from cogs.instagram import Instagram
from cogs.pixiv import Pixiv
from cogs.reddit import Reddit
from cogs.starboard import Starboard
from cogs.twitter import Twitter
from db import BotDB

BotDB.connect()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix = 'sb!', intents = intents)

@bot.event
async def on_ready():
	await bot.add_cog(Reddit(bot))
	await bot.add_cog(Instagram(bot))
	await bot.add_cog(Twitter())
	await bot.add_cog(Pixiv())
	await bot.add_cog(Starboard(bot))

	await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='the stars'))
	print(f'{bot.user.name} is ready.')

@bot.command(brief = 'Sets the bot up.')
@perms.mod()
async def setup(ctx: commands.Context, msg: discord.Message, archive_channel: str, archive_emote: str, archive_emote_amount: int):
	if BotDB.is_setup(msg.guild.id):
		await ctx.send('Bot has been setup already.')
		return

	BotDB.conn['server'].insert(dict(
		server_id = msg.guild.id,
		archive_channel = archive_channel.strip('<>#'),
		archive_emote = archive_emote,
		archive_emote_amount = archive_emote_amount
	))
	
	await ctx.send('Done.')

@bot.command(brief = 'Github page.')
async def source(ctx: commands.Context):
	ctx.send('<https://github.com/Roguezilla/starboard>')

@bot.command(brief = 'Pulls the latest version.')
@perms.owner()
async def pull(ctx: commands.Context):    
	pull = sp.Popen(['git', 'pull'], stdout=sp.PIPE)
	
	await ctx.send(f'```fix\n{pull.stdout.read().strip().decode("utf-8")[0:2048-10]}```')

@bot.command(brief = 'Restarts the bot.')
@perms.owner()
async def restart(ctx: commands.Context):
	await ctx.send('Restarting...')

	try: await bot.close()
	except: pass
	finally: sp.call([f'python{"3" if sys.platform == "linux" else ""}', 'main.py'])

@bot.command(brief='Debug')
@perms.owner()
async def run(ctx: commands.Context, code):
	try: out = eval(code)
	except Exception as e: out = str(e)[0:2048]
	finally:
		await ctx.send(embed=discord.Embed(title = code, description = out, color=0xffcc00).set_author(name = ctx.author.name, icon_url = ctx.author.avatar.url))
		await ctx.message.delete()

bot.run(BotDB.get_token())