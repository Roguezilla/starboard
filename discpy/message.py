import json
from datetime import datetime
from typing import List


def test(dict, key):
	return None if not dict else dict[key] if key in dict else None

class User:
	def __init__(self, user):
		self.username = test(user, 'username')
		self.id = test(user, 'id')
		# due to the bruh moment by discord from above we need to check if avatar actually exists instead of just checking if it's not None
		self.avatar_url = f'https://cdn.discordapp.com/avatars/{self.id}/{user["avatar"]}' if (self.id and test(user, 'avatar')) else None

		self.bot = test(user, 'bot')

		self.mention = f'<@{self.id}>' if self.id else ''

class Member(User):
	def __init__(self, user, member):
		super().__init__(user)

		self.roles = test(member, 'roles')

class Role:
	def __init__(self, role):
		self.id = role['id']
		self.permissions = role['permissions']

class Attachment:
	def __init__(self, attachment):
		self.url = attachment['url']
		self.is_spoiler = attachment['filename'].startswith('SPOILER_')

class Embed:
	class __Footer:
		def __init__(self, footer):
			self.text = footer['text']
			self.icon_url = test(footer, 'icon_url')
			self.proxy_icon_url = test(footer, 'proxy_icon_url')

	class __Image:
		def __init__(self, image):
			self.url = test(image, 'url')
			self.proxy_url = test(image, 'proxy_icon_url')
			self.height = test(image, 'height')
			self.width = test(image, 'width')

	class __Thumbnail:
		def __init__(self, thumbnail):
			self.url = test(thumbnail, 'url')
			self.proxy_url = test(thumbnail, 'proxy_icon_url')
			self.height = test(thumbnail, 'height')
			self.width = test(thumbnail, 'width')

	class __Video:
		def __init__(self, video):
			self.url = test(video, 'url')
			self.proxy_url = test(video, 'proxy_icon_url')
			self.height = test(video, 'height')
			self.width = test(video, 'width')

	class __Provider:
		def __init__(self, provider):
			self.name = test(provider, 'name')
			self.url = test(provider, 'url')

	class __Author:
		def __init__(self, author):
			self.name = test(author, 'name')
			self.url = test(author, 'url')
			self.icon_url = test(author, 'icon_url')
			self.proxy_icon_url = test(author, 'proxy_icon_url')

	class __Field:
		def __init__(self, field):
			self.name = field['name']
			self.value = field['value']
			self.inline = test(field, 'inline')

	def __init__(self, embed = {}, title = '', description = '', url = '', color = None):
		self.title = title if title else test(embed, 'title')
		self.type = test(embed, 'type')
		self.description = description if description else test(embed, 'description')
		self.url = url if url else test(embed, 'url')
		self.timestamp = datetime.fromisoformat(embed['timestamp']) if test(embed, 'timestamp') else None
		self.color = color if color else test(embed, 'color')
		self.footer = self.__Footer(embed['footer']) if test(embed, 'footer') else None
		self.image = self.__Image(embed['image']) if test(embed, 'image') else None
		self.thumbnail = self.__Thumbnail(embed['thumbnail']) if test(embed, 'thumbnail') else None
		self.video = self.__Video(embed['video']) if test(embed, 'video') else None
		self.provider = self.__Provider(embed['provider']) if test(embed, 'provider') else None
		self.author = self.__Author(embed['author']) if test(embed, 'author') else None
		
		self.fields: List[self.__Field] = []
		if test(embed, 'fields'):
			for field in embed['fields']:
				self.fields.append(self.__Field(field))
	
	def set_footer(self, text, icon_url = ''):
		self.footer = self.__Footer( { 'text': text, 'icon_url': icon_url } )

	def set_image(self, url):
		self.image = self.__Image( { 'url': url } )

	def set_thumbnail(self, url):
		self.thumbnail = self.__Thumbnail( { 'url': url } )
	
	def set_author(self, name = '', url = '', icon_url = ''):
		self.author = self.__Author( { 'name': name, 'url': url, 'icon_url': icon_url } )

	def add_field(self, name, value, inline=True):
		self.fields.append( self.__Field( {'name': name, 'value': value, 'inline': inline } ) )

	def set_field_at(self, idx, name, value, inline=True):
		self.fields[idx] = self.__Field( {'name': name, 'value': value, 'inline': inline } )

	def as_json(self):
  		return json.loads(
    		json.dumps(self, default=lambda o: getattr(o, '__dict__', str(o)))
  		)

class Emoji:
	def __init__(self, emoji):
		self.id = emoji['id']
		self.name = emoji['name']
		self.animated = test(emoji, 'animated')

	def __str__(self):
		# default emoji stuff
		if self.id == None:
			return self.name

		animated_prefix = 'a' if self.animated else ''
		return f'<{animated_prefix}:{self.name}:{self.id}>'

	def __eq__(self, o):
		return self.id == o.id and self.name == o.name

class Reaction:
	def __init__(self, reaction):
		self.count = reaction['count']
		self.emoji = Emoji(reaction['emoji'])

class Application:
	class Team:
		class Member:
			def __init__(self, member):
				self.user = User(member['user'])

		def __init__(self, team):
			self.members: List[self.Member] = []
			for member in team['members']:
				self.members.append(self.Member(member))

	def __init__(self, app):
		self.team = self.Team(app['team']) if test(app, 'team') else None
		self.owner = User(app['owner']) if test(app, 'owner') else None

class Message:
	class Reference:
		def __init__(self, ref):
			self.message_id = test(ref, 'message_id')

	def __init__(self, msg):
		self.id = msg['id']
		self.channel_id = msg['channel_id']
		self.guild_id = test(msg, 'guild_id')
		self.author = Member(msg['author'], test(msg, 'member'))
		self.content = msg['content']

		self.attachments: List[Attachment] = []
		for attachment in msg['attachments']:
			self.attachments.append(Attachment(attachment))

		self.embeds: List[Embed] = []
		for embed in msg['embeds']:
			self.embeds.append(Embed(embed))

		self.reactions: List[Reaction] = []
		if test(msg, 'reactions'):
			for reaction in msg['reactions']:
				self.reactions.append(Reaction(reaction))

		self.message_reference = self.Reference(msg['message_reference']) if test(msg, 'message_reference') else None