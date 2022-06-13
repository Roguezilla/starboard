import signal
import sys

# a ctrl+c handler is needed due to how starboard handles exceptions
signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

import psutil

# way to kill previous processes that triggered an exception and had to be restart
if len(sys.argv) > 1:
	# in theory this try except is not needed, but it's here just in case
	try:
		psutil.Process(int(sys.argv[1])).terminate()
	except psutil.NoSuchProcess: pass
		

import colorama

colorama.init(wrap=True)

import os
import subprocess as sp
import sys

from dataset import connect as db_connect

import perms
from cogs.pixiv import Pixiv
from cogs.reddit import Reddit
from cogs.starboard import Starboard
from discpy.discpy import DiscPy
from discpy.events import ReadyEvent
from discpy.message import Embed, Message

os.makedirs('logs', exist_ok=True)

db = db_connect('sqlite:///db.db')
bot = DiscPy(db['settings'].find_one(name='token')['value'], prefix='sb!', debug=1)

def query_servers(id):
	return db['server'].find_one(server_id = id)

"""
Events
"""
@bot.event()
async def on_ready(self: DiscPy, event: ReadyEvent):
	print(f'->Logged in as {event.user.username}')

	await self.update_presence('the stars.', self.ActivityType.WATCHING, self.Status.DND)

"""
Commands
"""
@bot.command()
@bot.permissions(perms.is_owner)
async def eval_code(self: DiscPy, msg: Message, *args):
	await self.send_message(msg.author.id, eval(' '.join(args)), is_dm = True)

@bot.command()
@bot.permissions(perms.is_mod)
async def setup(self: DiscPy, msg: Message, archive_channel: str, archive_emote: str, archive_emote_amount: int):
	if query_servers(msg.guild_id) is not None:
		await self.send_message(msg.channel_id, 'Bot has been setup already.')
		return

	db['server'].insert(dict(
		server_id = msg.guild_id,
		archive_channel = archive_channel.strip('<>#'),
		archive_emote = archive_emote,
		archive_emote_amount = archive_emote_amount,
		reddit_embed = True
	))

	await self.send_message(msg.channel_id, 'Done.')

@bot.command()
async def source(self: DiscPy, msg: Message):
	await self.send_message(msg.channel_id, '<https://github.com/Roguezilla/starboard>')

@bot.command()
@bot.permissions(perms.is_owner)
async def pull(self: DiscPy, msg: Message):	
	pull = sp.Popen(['git', 'pull'], stdout=sp.PIPE)
	
	embed = Embed(title='Update log', description=f'```{pull.stdout.read().strip().decode("utf-8")[0:2048-6]}```', color=0xffcc00)
	embed.set_footer('by rogue#0001')
	await self.send_message(msg.channel_id, embed=embed.as_json())

@bot.command()
@bot.permissions(perms.is_owner)
async def restart(self: DiscPy, msg: Message):
	await self.send_message(msg.channel_id, 'Restarting...')

	try: await bot.close()
	except: self.__log(f'Unable to close connection', 'err')
	# probably add macos later
	finally: os.system(f'{"python3" if sys.platform == "linux" else "python"} main.py {os.getpid()}')


"""
Cogs
"""
Starboard(bot, db)
Reddit(bot, db)
Pixiv(bot, db)

if __name__ == '__main__':
	bot.start()
