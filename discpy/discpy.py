import asyncio
import json
import os
import platform
from json.decoder import JSONDecodeError
from typing import Callable, Dict, List

import requests
import websockets

from .events import ReactionAddEvent, ReadyEvent
from .message import Application, Emoji, Member, Message, Reaction, Role, User


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
	
	def __init__(self, token, prefix=",", debug=1):
		self.__token = token
		self.__prefix = prefix
		self.__owner_ids = []
		self.__loop = asyncio.get_event_loop()
		self.__socket = None
		self.__BASE_API_URL = 'https://discord.com/api/v9'

		self.__sequence = None

		self.me: ReadyEvent = None

		self.__debug = 1

		self.__commands = {}

		self.__cogs: Dict[str, Callable]= {}
 
		self.__session = requests.Session()


	def start(self):
		self.__loop.create_task(self.__process_payloads())
		self.__loop.run_forever()

	def close(self):
		self.__loop.close()

	def __get_gateway(self):
		return self.__session.get(url = self.__BASE_API_URL + '/gateway', headers = { 'Authorization': f'Bot {self.__token}' }).json()['url'] + '/?v=9&encoding=json'

	def __log(self, log, level = 0):
		if self.__debug:
			level = '\033[92m[OK]\033[0m' if level == 0 else ('\033[96m[SOCKET]\033[0m' if level == 1 else '\033[91m[ERR]\033[0m')
			print(f'{level} {log}')

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
				'intents': intents, #32509 = basically all of them but the ones that need toggling options on the dashboard
				'properties': {
					'$os': platform.system(),
					'$browser': 'discpy',
					'$device': 'discpy'
				}
			}
		})
	
	def __resume_json(self):
		return json.dumps({
			'op': self.OpCodes.RESUME,
			'd': {
				'seq': self.__sequence,
				'session_id': self.me.session_id,
				'token': self.__token
			}
		})

	async def __do_heartbeats(self, interval):
		while True:
			payload = {
				'op': self.OpCodes.HEARTBEAT,
				'd': self.__sequence
			}
			await self.__socket.send(json.dumps(payload))

			if self.__debug:
				self.__log('Sent \033[93mHEARTBEAT\033[0m', 1)

			await asyncio.sleep(delay=interval / 1000)

	async def update_presence(self, name, type: ActivityType, status: Status):
		presence = {
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
		}
		
		await self.__socket.send(json.dumps(presence))

	async def __process_payloads(self):
		async with websockets.connect(self.__get_gateway()) as self.__socket:
			while True:
				raw_recv = await self.__socket.recv()
				try:
					recv_json = json.loads(raw_recv)

					if recv_json['s'] is not None:
						self.__sequence = recv_json['s']
					
					op = recv_json['op']
					if op != self.OpCodes.DISPATCH:
						if op == self.OpCodes.HELLO:
							self.__loop.create_task(self.__do_heartbeats(recv_json['d']['heartbeat_interval']))

							await self.__socket.send(self.__identify_json(intents=self.Intents.GUILD_MESSAGES | self.Intents.GUILD_MESSAGE_REACTIONS))
								
							self.__log('Sent \033[93mIDENTIFY\033[0m', 1)
								
						elif op == self.OpCodes.HEARTBEAT_ACK:
							self.__log('Got \033[93mHEARTBEAT_ACK\033[0m', 1)

						elif op == self.OpCodes.HEARTBEAT:
							await self.__socket.send(self.__hearbeat_json())

							self.__log('Forced \033[93mHEARTBEAT\033[0m', 1)

						elif op == self.OpCodes.RECONNECT:
							self.__log('Got \033[93mRECONNECT\033[0m', 1)

							self.__socket.send(self.__resume_json())

							self.__log('Sent \033[93mRESUME\033[0m', 1)
						
						elif op == self.OpCodes.INVALIDATE_SESSION:
							self.__log('Got \033[91mINVALIDATE_SESSION\033[0m', 1)

							self.__log('Restarting...', 2)

							try:
								await self.close()
							except:
								pass
							finally:
								os.system('python main.py')

						else:
							# the wrapper should probably handle opcode 9 :thinking:
							self.__log(f'Got \033[91munhanled\033[0m OpCode: \033[1m{op}\033[0m', 1)
					else:
						event = recv_json['t']
						if event == 'READY':
							self.__log('READY')

							self.me = ReadyEvent(recv_json['d'])

							if hasattr(self, 'on_ready'):
								await getattr(self, 'on_ready')(self, self.me)
						
						elif event == 'RESUMED':
							self.__log('RESUMED')

						elif event == 'MESSAGE_CREATE':
							def is_command(start):
								return start in self.__commands

							async def on_message(msg: Message):
								if msg.author.id == self.me.user.id:
									return
								
								split = msg.content.split(' ')
								if is_command(split[0]):
									if 'cond' in self.__commands[msg.content.split(' ')[0]]:
										if await self.__commands[msg.content.split(' ')[0]]['cond'](self, msg):
											await self.__commands[msg.content.split(' ')[0]]['func'](self, msg, *split[1:])
									else:
										await self.__commands[msg.content.split(' ')[0]]['func'](self, msg, *split[1:])

								if hasattr(self, 'on_message'):
									await getattr(self, 'on_message')(self, msg)

								for cog in self.__cogs:
									if 'on_message' in self.__cogs[cog]:
										await self.__cogs[cog]['on_message'](self, msg)

							await on_message(Message(recv_json['d']))

						elif event == 'MESSAGE_REACTION_ADD':
							if hasattr(self, 'on_reaction_add'):
								await getattr(self, 'on_reaction_add')(self, ReactionAddEvent(recv_json['d']))

							for cog in self.__cogs:
									if 'on_reaction_add' in self.__cogs[cog]:
										await self.__cogs[cog]['on_reaction_add'](self, ReactionAddEvent(recv_json['d']))

					self.__log(f'Sequence: \033[1m{self.__sequence}\033[0m', 1)

				except JSONDecodeError:
					self.__log('JSONDecodeError', 2)

	"""
	DECORATORS
	"""
	def command(self):
		def wrapper(func):
			if f'{self.__prefix}{func.__name__}' not in self.__commands:
				self.__commands[f'{self.__prefix}{func.__name__}'] = {}

			self.__commands[f'{self.__prefix}{func.__name__}']['func'] = func
			self.__log(f'Registed command: \033[93m{func.__name__}\033[0m')

			return func
		
		return wrapper

	def permissions(self, cond):
		def wrapper(func):
			if f'{self.__prefix}{func.__name__}' not in self.__commands:
				self.__commands[f'{self.__prefix}{func.__name__}'] = {}

			self.__commands[f'{self.__prefix}{func.__name__}']['cond'] = cond
			self.__log(f'Registed permissions for command: \033[93m{func.__name__}\033[0m')

			return func

		return wrapper

	def event(self, cog=None):
		def wrapper(func):
			if cog is not None and isinstance(cog, self.Cog):
				if cog not in self.__cogs:
					self.__cogs[cog] = {}

				self.__cogs[cog][func.__name__] = func
				self.__log(f'Registed cog event "\033[93m{func.__name__}\033[0m" for cog {cog}')
			else:
				setattr(self, func.__name__, func)
				self.__log(f'Registed event: \033[93m{func.__name__}\033[0m')

			return func
			
		return wrapper

	"""
	REST API
	"""
	async def send_message(self, channel_id, content = '', embed = None, is_dm = False) -> Message:
		data = {}
		if content:
			data['content'] = content
		
		if embed:
			data['embeds'] = [embed]

		if is_dm:
			resp = self.__session.post(
				self.__BASE_API_URL + '/users/@me/channels',
				headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' },
				json = {'recipient_id': channel_id}
			)

			if resp.status_code == 429:
				await asyncio.sleep(float(resp.headers["Retry-After"]))
				await self.send_message(channel_id, content, embed, is_dm)

				return

			channel_id = resp.json()['id']

		resp = self.__session.post(
			self.__BASE_API_URL + f'/channels/{channel_id}/messages',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' },
			data = json.dumps(data)
		)
	
		if resp.status_code == 429:
			await asyncio.sleep(float(resp.headers["Retry-After"]))
			return await self.send_message(channel_id, content, embed, is_dm)
		
		return Message(resp.json())

	async def edit_message(self, msg: Message, content = '', embed = None) -> Message:
		data = {}
		if content:
			data['content'] = content
		
		if embed:
			data['embeds'] = [embed]

		resp = self.__session.patch(
			self.__BASE_API_URL + f'/channels/{msg.channel_id}/messages/{msg.id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' },
			data = json.dumps(data)
		)

		if resp.status_code == 429:
			await asyncio.sleep(float(resp.headers["Retry-After"]))
			return await self.edit_message(msg.channel_id, msg.id, content, embed)

		return Message(resp.json())

	async def fetch_roles(self, guild_id) -> List[Role]:
		resp = self.__session.get(
			self.__BASE_API_URL + f'/guilds/{guild_id}/roles',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		if resp.status_code == 429:
			await asyncio.sleep(float(resp.headers["Retry-After"]))
			return await self.fetch_roles(guild_id)

		return [Role(role) for role in resp.json()]

	async def fetch_message(self, channel_id, message_id) -> Message:
		resp = self.__session.get(
			self.__BASE_API_URL + f'/channels/{channel_id}/messages/{message_id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		if resp.status_code == 429:
			await asyncio.sleep(float(resp.headers["Retry-After"]))
			return await self.fetch_message(channel_id, message_id)

		return Message(resp.json())

	async def delete_message(self, msg: Message):
		resp = self.__session.delete(
			self.__BASE_API_URL + f'/channels/{msg.channel_id}/messages/{msg.id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		if resp.status_code == 429:
			await asyncio.sleep(float(resp.headers["Retry-After"]))
			await self.delete_message(msg)

	async def add_reaction(self, msg: Message, emoji):
		def __convert(emoji):
			if isinstance(emoji, Reaction):
				emoji = emoji.emoji

			if isinstance(emoji, Emoji):
				return str(emoji)
			if isinstance(emoji, str):
				return emoji.strip('<>')
			
		resp = self.__session.put(
			self.__BASE_API_URL + f'/channels/{msg.channel_id}/messages/{msg.id}/reactions/{__convert(emoji)}/@me',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		if resp.status_code == 429:
			await asyncio.sleep(float(resp.headers["Retry-After"]))
			await self.add_reaction(msg, emoji)

	async def remove_reaction(self, msg: Message, member: Member, emoji):
		def __convert(emoji):
			if isinstance(emoji, Reaction):
				emoji = emoji.emoji

			if isinstance(emoji, Emoji):
				return str(emoji)
			if isinstance(emoji, str):
				return emoji.strip('<>')
			
		resp = self.__session.delete(
			self.__BASE_API_URL + f'/channels/{msg.channel_id}/messages/{msg.id}/reactions/{__convert(emoji)}/{member.id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		if resp.status_code == 429:
			await asyncio.sleep(float(resp.headers["Retry-After"]))
			await self.remove_reaction(msg, member, emoji)

	async def fetch_user(self, user_id) -> User:
		resp = self.__session.get(
			self.__BASE_API_URL + f'/users/{user_id}',
			headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
		)

		if resp.status_code == 429:
			await asyncio.sleep(float(resp.headers["Retry-After"]))
			return await self.fetch_user(user_id)

		return User(resp.json())

	"""
	HELPERS
	"""
	async def has_permissions(self, msg: Message, permission):
		guild_roles = await self.fetch_roles(msg.guild_id)
		for role in guild_roles:
			if next((r for r in msg.author.roles if r == role.id), None):
				return (int(role.permissions) & permission) == permission

		return False

	async def is_owner(self, id):
		if not self.__owner_ids:
			resp = self.__session.get(
				self.__BASE_API_URL + '/oauth2/applications/@me',
				headers = { 'Authorization': f'Bot {self.__token}', 'Content-Type': 'application/json', 'User-Agent': 'discpy' }
			)

			if resp.status_code == 429:
				await asyncio.sleep(float(resp.headers["Retry-After"]))
				await self.is_owner(id)

				return

			app = Application(resp.json())

			if app.team:
				member: Application.Team.Member
				for member in app.team.members:
					self.__owner_ids.append(member.user.id)
			else:
				self.__owner_ids.append(app.owner.id)

		return str(id) in self.__owner_ids
