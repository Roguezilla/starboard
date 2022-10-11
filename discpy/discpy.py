import asyncio
import json
import os
import sys
import time
import traceback
from typing import Callable, Dict, List

import requests
import websockets
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .events import ReactionAddEvent, ReadyEvent
from .message import Application, Emoji, Member, Message, Reaction, Role, User


# https://stackoverflow.com/a/51254525
class _CallbackRetry(Retry):
    def __init__(self, *args, **kwargs):
        self._callback = kwargs.pop('callback', None)
        super(_CallbackRetry, self).__init__(*args, **kwargs)
    def new(self, **kw):
        kw['callback'] = self._callback
        return super(_CallbackRetry, self).new(**kw)
    def increment(self, method, url, *args, **kwargs):
        self._callback(url)
        return super(_CallbackRetry, self).increment(method, url, *args, **kwargs)

class DiscPy:
	class OpCodes:
		DISPATCH = 0
		HEARTBEAT = 1
		IDENTIFY = 2
		PRESENCE = 3
		VOICE_STATE = 4
		VOICE_PING = 5
		RESUME = 6
		RECONNECT = 7
		REQUEST_MEMBERS = 8
		INVALIDATE_SESSION = 9
		HELLO = 10
		HEARTBEAT_ACK = 11
		GUILD_SYNC = 12

	class Status:
		ONLINE = 'online'
		OFFLINE = 'offline'
		IDLE = 'idle'
		DND = 'dnd'
		INVISIBLE = 'invisible'

	class ActivityType:
		UNKNOWN = -1
		PLAYING = 0
		STREAMING = 1
		LISTENING = 2
		WATCHING = 3
		CUSTOM = 4
		COMPETING = 5

	class Intents:
		GUILDS = (1 << 0)
		"""
		- GUILD_CREATE
		- GUILD_UPDATE
		- GUILD_DELETE
		- GUILD_ROLE_CREATE
		- GUILD_ROLE_UPDATE
		- GUILD_ROLE_DELETE
		- CHANNEL_CREATE
		- CHANNEL_UPDATE
		- CHANNEL_DELETE
		- CHANNEL_PINS_UPDATE
		- THREAD_CREATE
		- THREAD_UPDATE
		- THREAD_DELETE
		- THREAD_LIST_SYNC
		- THREAD_MEMBER_UPDATE
		- THREAD_MEMBERS_UPDATE *
		- STAGE_INSTANCE_CREATE
		- STAGE_INSTANCE_UPDATE
		- STAGE_INSTANCE_DELETE
		"""

		GUILD_MEMBERS = (1 << 1)
		"""
		- GUILD_MEMBER_ADD
		- GUILD_MEMBER_UPDATE
		- GUILD_MEMBER_REMOVE
		- THREAD_MEMBERS_UPDATE *
		"""

		GUILD_BANS = (1 << 2)
		"""
		- GUILD_BAN_ADD
		- GUILD_BAN_REMOVE
		"""

		GUILD_EMOJIS = (1 << 3)
		"""
		- GUILD_EMOJIS_UPDATE
		"""

		GUILD_INTEGRATIONS = (1 << 4)
		"""
		- GUILD_INTEGRATIONS_UPDATE
		- INTEGRATION_CREATE
		- INTEGRATION_UPDATE
		- INTEGRATION_DELETE
		"""

		GUILD_WEBHOOKS = (1 << 5)
		"""
		- WEBHOOKS_UPDATE
		"""

		GUILD_INVITES = (1 << 6)
		"""
		- INVITE_CREATE
		- INVITE_DELETE
		"""

		GUILD_VOICE_STATES = (1 << 7)
		"""
		- VOICE_STATE_UPDATE
		"""

		GUILD_PRESENCES = (1 << 8)
		"""
		- PRESENCE_UPDATE
		"""

		GUILD_MESSAGES = (1 << 9)
		"""
		- MESSAGE_CREATE
		- MESSAGE_UPDATE
		- MESSAGE_DELETE
		- MESSAGE_DELETE_BULK
		"""

		GUILD_MESSAGE_REACTIONS = (1 << 10)
		"""
		- MESSAGE_REACTION_ADD
		- MESSAGE_REACTION_REMOVE
		- MESSAGE_REACTION_REMOVE_ALL
		- MESSAGE_REACTION_REMOVE_EMOJI
		"""

		GUILD_MESSAGE_TYPING = (1 << 11)
		"""
		- TYPING_START
		"""

		DIRECT_MESSAGES = (1 << 12)
		"""
		- MESSAGE_CREATE
		- MESSAGE_UPDATE
		- MESSAGE_DELETE
		- CHANNEL_PINS_UPDATE
		"""

		DIRECT_MESSAGE_REACTIONS = (1 << 13)
		"""
		- MESSAGE_REACTION_ADD
		- MESSAGE_REACTION_REMOVE
		- MESSAGE_REACTION_REMOVE_ALL
		- MESSAGE_REACTION_REMOVE_EMOJI
		"""

		DIRECT_MESSAGE_TYPING = (1 << 14)
		"""
		- TYPING_START
		"""

		MESSAGE_CONTENT = (1 << 15)

	class Permissions:
		CREATE_INSTANT_INVITE = (1 << 0)
		KICK_MEMBERS = (1 << 1)
		BAN_MEMBERS = (1 << 2)
		ADMINISTRATOR = (1 << 3)
		MANAGE_CHANNELS = (1 << 4)
		MANAGE_GUILD = (1 << 5)
		ADD_REACTIONS = (1 << 6)
		VIEW_AUDIT_LOG = (1 << 7)
		PRIORITY_SPEAKER = (1 << 8)
		STREAM = (1 << 9)
		VIEW_CHANNEL = (1 << 10)
		SEND_MESSAGES = (1 << 11)
		SEND_TTS_MESSAGES = (1 << 12)
		MANAGE_MESSAGES = (1 << 13) 
		EMBED_LINKS = (1 << 14)
		ATTACH_FILES = (1 << 15)
		READ_MESSAGE_HISTORY = (1 << 16)
		MENTION_EVERYONE = (1 << 17)
		USE_EXTERNAL_EMOJIS = (1 << 18)
		VIEW_GUILD_INSIGHTS = (1 << 19)
		CONNECT = (1 << 20)
		SPEAK = (1 << 21)
		MUTE_MEMBERS = (1 << 22)
		DEAFEN_MEMBERS = (1 << 23)
		MOVE_MEMBERS = (1 << 24)
		USE_VAD = (1 << 25)
		CHANGE_NICKNAME = (1 << 26)
		MANAGE_NICKNAMES = (1 << 27)
		MANAGE_ROLES = (1 << 28)
		MANAGE_WEBHOOKS = (1 << 29)
		MANAGE_EMOJIS_AND_STICKERS = (1 << 30)
		USE_APPLICATION_COMMANDS = (1 << 31)
		REQUEST_TO_SPEAK = (1 << 32)
		MANAGE_THREADS = (1 << 34)
		CREATE_PUBLIC_THREADS = (1 << 35)
		CREATE_PRIVATE_THREADS = (1 << 36)
		USE_EXTERNAL_STICKERS = (1 << 37)
		SEND_MESSAGES_IN_THREADS = (1 << 38)
		START_EMBEDDED_ACTIVITIES = (1 << 39)

	# dummy class
	class Cog:
		pass
	
	session = requests.Session()
	def __init__(self, token, prefix=",", debug=0):
		self.__BASE_API_URL = 'https://discord.com/api/v10'
		self.__GATEWAY_URL = ''

		self.__token = token
		self.__prefix = prefix
		self.__owner_ids = []
		self.__debug = debug

		self.__event_loop = asyncio.get_event_loop()
		self.__socket = None
		retry = _CallbackRetry(
			total=10,
			status_forcelist=[429],
			method_whitelist=False,
			respect_retry_after_header=True,
			callback=lambda x: self.__log(f'Retrying for {x}', 'http')
		)
		DiscPy.session.mount('https://', HTTPAdapter(max_retries=retry))

		self.me: ReadyEvent = None
		self.__sequence = None

		self.__commands = {}
		self.__cogs: Dict[str, Callable] = {}

		self.python_command = f'python{"3" if sys.platform == "linux" else ""}'

		self.__got_first_ack = False
		self.__hb_got_resp = False

	def start(self):
		self.__event_loop.create_task(self.__process_payloads())
		self.__event_loop.run_forever()

	async def close(self):
		await self.__socket.close()

	def __get_gateway(self):
		if self.__GATEWAY_URL == '':
			self.__GATEWAY_URL = DiscPy.session.get(url = self.__BASE_API_URL + '/gateway', headers = { 'Authorization': f'Bot {self.__token}' }).json()['url'] + '/?v=10&encoding=json'

		return self.__GATEWAY_URL

	def __log(self, log, level = 'ok'):
		if self.__debug:
			prefix = ''
			if level == 'ok':
				prefix = '\033[92m[OK]\033[0m'
			elif level == 'socket':
				prefix = '\033[96m[SOCKET]\033[0m'
			elif level == 'http':
				prefix = '\033[94m[HTTP]\033[0m'
			elif level ==  'err':
				prefix = '\033[91m[ERR]\033[0m'
			
			print(f'{prefix} {log}')

	def __hearbeat_json(self):
		return json.dumps({
			'op': self.OpCodes.HEARTBEAT,
			'd': self.__sequence
		})

	def __identify_json(self, intents):
		return json.dumps({
			'op': self.OpCodes.IDENTIFY,
			'd': {
				'token': self.__token,
				'intents': intents,
				'properties': {
					'$os': sys.platform,
					'$browser': 'discpy',
					'$device': 'discpy'
				}
			}
		})

	def __resume_json(self):
		return json.dumps({
			'op': self.OpCodes.RESUME,
			'd': {
				'token': self.__token,
				'session_id': self.me.session_id,
				'seq': self.__sequence
			}
		})

	async def __do_heartbeats(self, interval):
		try:
			while self.__socket.open:
				# if by the time it's time to send a new heartbeat we haven't gotten
				# a response to the previous one, it's time to restart the bot
				if self.__got_first_ack and not self.__hb_got_resp:
					raise Exception

				# this should never throw any exception due to "while self.__socket.open:"
				await self.__socket.send(self.__hearbeat_json())

				self.__log('Sent \033[93mHEARTBEAT\033[0m', 'socket')

				self.__hb_got_resp = False
				await asyncio.sleep(delay=interval / 1000)
		except:
			self.__log('Previous \033[93mHEARTBEAT\033[0m didn\'t get a \033[93mHEARTBEAT_ACK\033[0m in time.', 'socket')

			try: await self.close()
			# in theory, no exceptions will be throws but you can never be sure...
			except: self.__log(f'__do_heartbeats -> Unable to close connection because it\'t already closed.', 'err')

			os.system(f'{self.python_command} main.py {os.getpid()}')

	async def update_presence(self, name, type: ActivityType, status: Status):		
		await self.__socket.send(json.dumps({
			'op': self.OpCodes.PRESENCE,
			'd': {
				'since': None,
				'activities': [{
					'name': name,
					'type': type
				}],
				'status': status,
				'afk': False
			}
		}))

	async def __process_payloads(self):
		try:
			async with websockets.connect(self.__get_gateway()) as self.__socket:
				while self.__socket.open:
					recv_json = json.loads(await self.__socket.recv())
					
					if recv_json['s']:
						self.__sequence = recv_json['s']

					if recv_json['op'] == self.OpCodes.HELLO:
						self.__event_loop.create_task(self.__do_heartbeats(recv_json['d']['heartbeat_interval']))
					elif recv_json['op'] ==  self.OpCodes.HEARTBEAT_ACK:
						self.__log('Got \033[93mHEARTBEAT_ACK\033[0m', 'socket')
						self.__hb_got_resp = True

						# we only want to send this when we are sure a connection has been properly established
						if not self.__got_first_ack:
							await self.__socket.send(self.__identify_json(intents=self.Intents.GUILD_MESSAGES | self.Intents.GUILD_MESSAGE_REACTIONS | self.Intents.MESSAGE_CONTENT))
							
							self.__log('Sent \033[93mIDENTIFY\033[0m', 'socket')
							self.__got_first_ack = True
					elif recv_json['op'] ==  self.OpCodes.HEARTBEAT:
						await self.__socket.send(self.__hearbeat_json())

						self.__log('Forced \033[93mHEARTBEAT\033[0m', 'socket')
					elif recv_json['op'] ==  self.OpCodes.RECONNECT or recv_json['op'] == self.OpCodes.INVALIDATE_SESSION:
						self.__log('Got \033[93mRECONNECT\033[0m or \033[91mINVALIDATE_SESSION\033[0m', 'socket')
						self.__log('Restarting because I ain\'t implementing discord\'s fancy resume shit.', 'err')

						await self.close()
						os.system(f'{self.python_command} main.py {os.getpid()}')
					elif recv_json['op'] ==  self.OpCodes.DISPATCH:
						if recv_json['t'] == 'READY':
							self.me = ReadyEvent(recv_json['d'])

							if hasattr(self, 'on_ready'):
								await getattr(self, 'on_ready')(self.me)
						elif recv_json['t'] == 'MESSAGE_CREATE':
							async def on_message(msg: Message):
								if msg.author.id == self.me.user.id:
									return
								
								split = msg.content.split(' ')
								if split[0] in self.__commands:
									if 'cond' in self.__commands[split[0]]:
										if await self.__commands[split[0]]['cond'](self, msg):
											await self.__commands[split[0]]['func'](msg, *split[1:])
									else:
										await self.__commands[split[0]]['func'](msg, *split[1:])

								if hasattr(self, 'on_message'):
									await getattr(self, 'on_message')(msg)

								for cog in self.__cogs:
									if 'on_message' in self.__cogs[cog]:
										await self.__cogs[cog]['on_message'](msg)

							await on_message(Message(recv_json['d']))
						elif recv_json['t'] == 'MESSAGE_REACTION_ADD':
							if hasattr(self, 'on_reaction_add'):
								await getattr(self, 'on_reaction_add')(ReactionAddEvent(recv_json['d']))

							for cog in self.__cogs:
								if 'on_reaction_add' in self.__cogs[cog]:
									await self.__cogs[cog]['on_reaction_add'](ReactionAddEvent(recv_json['d']))
						#else:
						#	self.__log(f'Got \033[91munhanled\033[0m event: \033[1m{recv_json["t"]}\033[0m', 'socket')
					else:
						self.__log(f'Got \033[91munhanled\033[0m OpCode: \033[1m{recv_json["op"]}\033[0m', 'socket')

					self.__log(f'Sequence: \033[1m{self.__sequence}\033[0m', 'socket')
		except:
			try:
				if 'websockets.exceptions.ConnectionClosed' not in traceback.format_exc():
					open(f'logs/{time.asctime().replace(":", " ")}.txt', 'w').write(traceback.format_exc())
			except: self.__log(f'Unable to create log file for exception', 'err')
		finally:
			# this is needed due to "while self.__socket.open" at least according to this error i managed
			# to somehow get where self.__socket was None after "establishing" a connection
			try: await self.close()
			except: self.__log(f'__process_payloads -> Unable to close connection because it\'s already closed or failed to open.', 'err')

			os.system(f'{self.python_command} main.py {os.getpid()}')

	"""
	DECORATORS
	"""
	def command(self, cog=None):
		def wrapper(func):
			if f'{self.__prefix}{func.__name__}' not in self.__commands:
				self.__commands[f'{self.__prefix}{func.__name__}'] = {}

			self.__commands[f'{self.__prefix}{func.__name__}']['func'] = func
			self.__log(f'Registed command \033[93m{func.__name__}\033[0m{" for " + str(cog).split(" ")[0][1::] if isinstance(cog, self.Cog) else ""}')

			return func
		
		return wrapper

	def permissions(self, cond):
		def wrapper(func):
			if f'{self.__prefix}{func.__name__}' not in self.__commands:
				self.__commands[f'{self.__prefix}{func.__name__}'] = {}

			self.__commands[f'{self.__prefix}{func.__name__}']['cond'] = cond
			self.__log(f'Registed permissions for command \033[93m{func.__name__}\033[0m')

			return func

		return wrapper

	def event(self, cog=None):
		def wrapper(func):
			if isinstance(cog, self.Cog):
				if cog not in self.__cogs:
					self.__cogs[cog] = {}

				self.__cogs[cog][func.__name__] = func
				self.__log(f'Registed cog event "\033[93m{func.__name__}\033[0m" for {str(cog).split(" ")[0][1::]}')
			else:
				setattr(self, func.__name__, func)
				self.__log(f'Registed event \033[93m{func.__name__}\033[0m')

			return func
			
		return wrapper

	"""
	REST API
	"""
	async def send_message(self, channel_id, content = '', embed = None, is_dm = False) -> Message:
		data = {}
		if content: data['content'] = content
		if embed: data['embeds'] = embed if type(embed) == list else [embed]

		if is_dm:
			resp = DiscPy.session.post(
				self.__BASE_API_URL + '/users/@me/channels',
				headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' },
				json = {'recipient_id': channel_id}
			)

			channel_id = resp.json()['id']

		resp = DiscPy.session.post(
			self.__BASE_API_URL + f'/channels/{channel_id}/messages',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' },
			data = json.dumps(data)
		)
		
		# request went through but no message was sent, i wasn't able
		# replicate the error on my pc, but this should fix it according
		# to the error file
		if 'id' not in resp.json():
			return await self.send_message(channel_id, content, embed, is_dm)
		
		return Message(resp.json())

	async def edit_message(self, msg: Message, content = '', embed = None) -> Message:
		data = {}
		if content: data['content'] = content
		if embed: data['embeds'] = [embed]

		resp = DiscPy.session.patch(
			self.__BASE_API_URL + f'/channels/{msg.channel_id}/messages/{msg.id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' },
			data = json.dumps(data)
		)

		return Message(resp.json())

	async def fetch_roles(self, guild_id) -> List[Role]:
		resp = DiscPy.session.get(
			self.__BASE_API_URL + f'/guilds/{guild_id}/roles',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		return [Role(role) for role in resp.json()]

	async def fetch_message(self, channel_id, message_id) -> Message:
		resp = DiscPy.session.get(
			self.__BASE_API_URL + f'/channels/{channel_id}/messages/{message_id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		return Message(resp.json())

	async def delete_message(self, msg: Message):
		DiscPy.session.delete(
			self.__BASE_API_URL + f'/channels/{msg.channel_id}/messages/{msg.id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

	def __convert(self, emoji):
		if isinstance(emoji, Reaction):
			emoji = emoji.emoji

		if isinstance(emoji, Emoji) or isinstance(emoji, str):
			if len(str(emoji)) == 1:
				return str(emoji)
			else:
				return str(emoji).strip('<>').replace(':', '', 0 if str(emoji)[1] == "a" else 1)
	
	async def add_reaction(self, msg: Message, emoji, unicode=False):
		DiscPy.session.put(
			self.__BASE_API_URL + f'/channels/{msg.channel_id}/messages/{msg.id}/reactions/{self.__convert(emoji) if not unicode else emoji}/@me',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

	async def remove_reaction(self, msg: Message, member: Member, emoji):		
		DiscPy.session.delete(
			self.__BASE_API_URL + f'/channels/{msg.channel_id}/messages/{msg.id}/reactions/{self.__convert(emoji)}/{member.id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

	async def fetch_emoji_count(self, msg: Message, emoji):
		resp = DiscPy.session.get(
			self.__BASE_API_URL + f'/channels/{msg.channel_id}/messages/{msg.id}/reactions/{self.__convert(emoji)}?limit=100',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		return len(resp.json())

	async def fetch_user(self, user_id) -> User:
		resp = DiscPy.session.get(
			self.__BASE_API_URL + f'/users/{user_id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		return User(resp.json())

	"""
	HELPERS
	"""
	async def has_permissions(self, msg: Message, permission):
		#TODO: channel permissions override role permissions or something
		has_perm = False
		for role in await self.fetch_roles(msg.guild_id):
			if next((r for r in msg.author.roles if r == role.id), None):
				has_perm |= (int(role.permissions) & permission) == permission

		return has_perm

	async def is_owner(self, id):
		if not self.__owner_ids:
			resp = DiscPy.session.get(
				self.__BASE_API_URL + '/oauth2/applications/@me',
				headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
			)

			app = Application(resp.json())
			if app.team:
				member: Application.Team.Member
				for member in app.team.members:
					self.__owner_ids.append(member.user.id)
			else:
				self.__owner_ids.append(app.owner.id)

		return str(id) in self.__owner_ids
