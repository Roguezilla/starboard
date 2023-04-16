import subprocess as sp

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
	for member in (await bot.application_info()).team.members:
		bot.owner_ids.add(member.id)

	await bot.add_cog(Reddit(bot))
	await bot.add_cog(Instagram(bot))
	await bot.add_cog(Twitter())
	await bot.add_cog(Pixiv())
	await bot.add_cog(Starboard(bot))

	await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='the stars'))

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
	
	await ctx.send(embed=discord.Embed(description=f'```diff\n{pull.stdout.read().strip().decode("utf-8")[0:2048-12]}```', color=0xffcc00))

@bot.command(brief = 'Restarts the bot.')
@perms.owner()
async def restart(ctx: commands.Context):
	await ctx.send('Restarting...')

	try: await bot.close()
	except KeyboardInterrupt: pass
	finally: sp.call(["python", "main.py"])

@bot.command(brief = 'Stops the bot.')
@perms.owner()
async def stop(ctx: commands.Context):
	await bot.close()

@bot.command(brief='Debug')
@perms.owner()
async def eval_code(ctx: commands.Context, *args):
	await (await bot.fetch_user(bot.owner_id)).send(eval(' '.join(args)))

bot.run(BotDB.get_token())