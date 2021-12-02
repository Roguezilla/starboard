from dataset import connect as db_connect

from discpy.discpy import DiscPy
from discpy.events import ReactionAddEvent, ReadyEvent
from discpy.message import Embed, Message

db = db_connect('sqlite:///db.db')

bot = DiscPy(db['settings'].find_one(name='token')['value'], prefix='sb!', debug=1)

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
async def source(self: DiscPy, msg: Message):
	await self.send_message(msg.channel_id, 'https://github.com/Roguezilla/starboard')

bot.start()
