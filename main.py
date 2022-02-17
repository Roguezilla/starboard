import os

from dataset import connect as db_connect

import perms
from cogs.reddit import Reddit
from cogs.starboard import Starboard
from discpy.discpy import DiscPy
from discpy.events import ReadyEvent
from discpy.message import Message

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
async def restart(self: DiscPy, msg: Message):
	await self.send_message(msg.channel_id, 'Restarting...')

	try: await bot.close()
	finally: os.system('python main.py')

@bot.command()
@bot.permissions(perms.is_owner)
async def pull(self: DiscPy, msg: Message):
	await self.send_message(msg.channel_id, 'Updating...')
	os.system('git pull')
	await self.send_message(msg.channel_id, 'Updated.')

"""
Cogs
"""
Starboard(bot, db)
Reddit(bot, db)

if __name__ == '__main__':
	bot.start()
