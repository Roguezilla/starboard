import os
import subprocess as sp
import sys

import colorama
import psutil

import perms
from cogs.custom_embeds import CustomEmbeds
from cogs.pixiv import BetterPixiv
from cogs.starboard import Starboard
from cogs.twitter import BetterTwitter
from db import BotDB
from discpy.discpy import DiscPy
from discpy.events import ReadyEvent
from discpy.message import Embed, Message

# way to kill previous processes that triggered an exception and had to be restarted
if len(sys.argv) > 1:
	# in theory this try except is not needed, but it's here just in case
	try: psutil.Process(int(sys.argv[1])).terminate()
	except psutil.NoSuchProcess: pass

# windows' default cmd can't handle colors properly without this
colorama.init(wrap=True)

BotDB.connect()
bot = DiscPy(BotDB.get_token(), prefix='sb!', debug=1)

"""
Events
"""
@bot.event()
async def on_ready(event: ReadyEvent):
	print(f'->Logged in as {event.user.username}')

	await bot.update_presence('the stars.', bot.ActivityType.WATCHING, bot.Status.DND)

"""
Commands
"""
@bot.command()
@bot.permissions(perms.is_owner)
async def eval_code(msg: Message, *args):
	await bot.send_message(msg.author.id, eval(' '.join(args)), is_dm = True)

@bot.command()
@bot.permissions(perms.is_mod)
async def setup(msg: Message, archive_channel: str, archive_emote: str, archive_emote_amount: int):
	if BotDB.is_setup(msg.guild_id):
		await bot.send_message(msg.channel_id, 'Bot has been setup already.')
		return

	BotDB.conn['server'].insert(dict(
		server_id = msg.guild_id,
		archive_channel = archive_channel.strip('<>#'),
		archive_emote = archive_emote,
		archive_emote_amount = archive_emote_amount
	))

	await bot.send_message(msg.channel_id, 'Done.')

@bot.command()
async def source(msg: Message):
	await bot.send_message(msg.channel_id, '<https://github.com/Roguezilla/starboard>')

@bot.command()
@bot.permissions(perms.is_owner)
async def pull(msg: Message):	
	pull = sp.Popen(['git', 'pull'], stdout=sp.PIPE)
	
	embed = Embed(title='Update log', description=f'```{pull.stdout.read().strip().decode("utf-8")[0:2048-6]}```', color=0xffcc00)
	embed.set_footer('by rogue#0001')
	await bot.send_message(msg.channel_id, embed=embed.as_json())

@bot.command()
@bot.permissions(perms.is_owner)
async def restart(msg: Message):
	await bot.send_message(msg.channel_id, 'Restarting...')

	await bot.close()
	os.system(f'{bot.python_command} main.py {os.getpid()}')


"""
Cogs
"""
Starboard(bot)
CustomEmbeds(bot)
BetterPixiv(bot)
BetterTwitter(bot)

if __name__ == '__main__':
	try: bot.start()
	except KeyboardInterrupt: sys.exit()
