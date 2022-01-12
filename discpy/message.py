import json
from datetime import datetime
from typing import List


def test(dict, key):
	return None if not dict else dict[key] if key in dict else None

class User:
	def __init__(self, user):
		"""
		so there's this thing called "Guild Member Structure" which has all the relevant info about a user,
		for some the "user" field in it can be null in MESSAGE_CREATE and MESSAGE_UPDATE
		what's worse is that the payloads of those events have a field called "user" which is basically the same
		thing as "user" but it's in a separate field instead of being inside "member" as a "user" object
		"""

		self.username = test(user, 'username')
		self.id = test(user, 'id')
		self.discriminator = test(user, 'discriminator')
		# due to the bruh moment by discord from above we need to check if avatar actually exists instead of just checking if it's not None
		self.avatar_url = f'https://cdn.discordapp.com/avatars/{self.id}/{user["avatar"]}' if (self.id and test(user, 'avatar')) else None

		self.bot = test(user, 'bot')
		self.system = test(user, 'system')
		self.mfa_enabled = test(user, 'mfa_enabled')
		self.locale = test(user, 'locale')
		self.verified = test(user, 'verified')
		self.email = test(user, 'email')
		self.flags = test(user, 'flags')
		self.premium_type = test(user, 'premium_type')
		self.public_flags = test(user, 'public_flags')

		self.mention = f'<@{self.id}>' if self.id else ''

class Member(User):
	def __init__(self, user, member):
		super().__init__(user)

		"""
		DISCORD IS CODED BY MONKEYS, so we have to run test() on all keys instead of only like 4
		why? well, read ** of https://discord.com/developers/docs/resources/channel#message-object
		"""

		self.nick = test(member, 'nick')
		self.roles = test(member, 'roles')
		self.joined_at = datetime.fromisoformat(member['joined_at']) if test(member, 'joined_at') else None
		# premium is an optional_and_nullable_field
		# https://discord.com/developers/docs/reference#nullable-and-optional-resource-fields-example-nullable-and-optional-fields
		self.premium_since = datetime.fromisoformat(member['premium_since']) if test(member, 'premium_since') else None
		self.deaf = test(member, 'deaf')
		self.mute = test(member, 'mute')
		self.pending = test(member, 'pending')
		# this field is fucking useless, thanks discord!
		self.permissions = test(member, 'permissions')	

class Role:
	class RoleTags:
		def __init__(self, tags) -> None:
			self.bot_id = test(tags, 'bot_id')
			self.integration_id = test(tags, 'integration_id')
			self.premium_subscriber = test(tags, 'premium_subscriber')

	def __init__(self, role):
		self.id = role['id']
		self.name = role['name']
		self.color = role['color']
		self.hoist = role['hoist']
		self.position = role['position']
		self.permissions = role['permissions']
		self.managed = role['managed']
		self.mentionable = role['mentionable']
		self.tags = self.RoleTags(role['tags']) if test(role, 'tags') else None

		self.mention = f'<@&{self.id}>'

class ChannelMention:
	def __init__(self, mention_channel):
		self.id = mention_channel['id']
		self.guild_id = mention_channel['guild_id']
		self.type = mention_channel['type']
		self.name = mention_channel['name']

class Attachment:
	def __init__(self, attachment):
		self.id = attachment['id']
		self.filename = attachment['filename']
		self.content_type = test(attachment, 'content_type')
		self.size = attachment['size']
		self.url = attachment['url']
		self.proxy_url = attachment['proxy_url']
		self.width = test(attachment, 'width')
		self.height = test(attachment, 'height')
		self.is_spoiler = self.filename.startswith('SPOILER_')

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

		self.roles: List[Role] = []
		if test(emoji, 'roles'):
			for role in emoji['roles']:
				self.roles.append(role)

		self.user = User(emoji['user']) if test(emoji, 'user') else None
		self.require_colons = test(emoji, 'require_colons')
		self.managed = test(emoji, 'managed')
		self.animated = test(emoji, 'animated')
		self.available = test(emoji, 'available')

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
		self.me = reaction['me']
		self.emoji = Emoji(reaction['emoji'])

class MessageActivity:
	class Type:
		JOIN = 1
		SPECTATE = 2
		LISTEN = 3
		JOIN_REQUEST = 5 

	def __init__(self, activity):
		self.type: self.Type = activity['type']
		self.party_id = test(activity, 'party_id')

class Application:
	class Team:
		class Member:
			def __init__(self, member):
				self.membership_state = member['membership_state']
				self.permissions = member['permissions']
				self.team_id = member['team_id']
				self.user = User(member['user'])

		def __init__(self, team):
			self.icon = team['icon']
			self.id = team['id']

			self.members: List[self.Member] = []
			for member in team['members']:
				self.members.append(self.Member(member))

			self.name = team['name']

			self.owner_user_id = team['owner_user_id']

	def __init__(self, app):
		"""
		in today's episode of discord is ran by monkeys:
		https://discord.com/developers/docs/topics/gateway#ready sends a "partial application object" which "contains id and flags"
		https://discord.com/developers/docs/resources/application#application-object says that there are 8(?) non optional keys
		so now they must be test()'d because some dev decided to go against docs
		"""
		self.id = app['id']
		self.name = test(app, 'name')
		self.icon = test(app, 'icon')
		self.description = test(app, 'description')
		self.rpc_origins = test(app, 'rpc_origins')
		self.bot_public = test(app, 'bot_public')
		self.bot_require_code_grant = test(app, 'bot_require_code_grant')
		self.terms_of_service_url = test(app, 'terms_of_service_url')
		self.privacy_policy_url = test(app, 'privacy_policy_url')
		self.owner = User(app['owner']) if test(app, 'owner') else None
		self.summary = test(app, 'summary')
		self.verify_key = test(app, 'verify_key')
		self.team = self.Team(app['team']) if test(app, 'team') else None
		self.guild_id = test(app, 'guild_id')
		self.primary_sku_id = test(app, 'primary_sku_id')
		self.slug = test(app, 'slug')
		self.cover_image = test(app, 'cover_image')
		self.flags = test(app, 'flags')

class MessageReference:
	def __init__(self, reference):
		self.message_id = test(reference, 'message_id')
		self.channel_id = test(reference, 'channel_id')
		self.guild_id = test(reference, 'guild_id')
		self.fail_if_not_exists = test(reference, 'fail_if_not_exists')

class Component:
		class Type:
			ACTION_ROW = 1
			BUTTON = 2
			SELECT_MENU = 3
		
		def __init__(self, component):
			self.type: self.Type = component['type']
			self.style = test(component, 'style')
			self.label = test(component, 'label')
			self.emoji = Emoji(component['emoji']) if test(component, 'emoji') else None
			self.custom_id = test(component, 'custom_id')
			self.url = test(component, 'url')
			self.disabled = test(component, 'disabled')
			
			self.components: List[self] = []
			if test(component, 'components'):
				for component in component['components']:
					self.components.append(self(component))

class MessageInteraction:
	class __AllowedMentions:
		def __init__(self, allowed) -> None:
			self.parse = allowed['parse']
			self.roles = allowed['roles']
			self.users = allowed['users']
			self.replied_user = allowed['replied_user']

	def __init__(self, interaction):
		self.tts = test(interaction, 'tts')
		self.content = test(interaction, 'content')
		
		self.embeds: List[Embed] = []
		if test(interaction, 'embeds'):
			for embed in interaction['embeds']:
				self.embeds.append(embed)
		
		self.allowed_mentions = self.__AllowedMentions(interaction['allowed_mentions']) if test(interaction, 'allowed_mentions') else None
		self.flags = test(interaction, 'flags')

		self.components: List[Component] = []
		if test(interaction, 'components'):
			for component in interaction['components']:
				self.components.append(Component(component))

class PermissionOverwrite:
	def __init__(self, overwrite):
		self.id = overwrite['id']
		self.type = overwrite['type']
		self.allow = overwrite['allow']
		self.deny = overwrite['deny']

class ThreadMetadata:
	def __init__(self, metadata):
		self.archived = metadata['archived']
		self.auto_archive_duration = metadata['auto_archive_duration']
		self.archive_timestamp = datetime.fromisoformat(metadata['archive_timestamp'])
		self.locked = test(metadata, 'locked')

class ThreadMember:
	def __init__(self, member):
		self.id = test(member, 'id')
		self.user_id = test(member, 'user_id')
		self.join_timestamp = datetime.fromisoformat(member['join_timestamp'])
		self.flags = member['flags']

class TextChannel:
	def __init__(self, channel):
		self.id = channel['id']
		self.type = channel['type']
		self.guild_id = test(channel, 'channel')
		self.position = test(channel, 'position')
		
		self.permission_overwrites: List[PermissionOverwrite] = []
		if test(channel, 'permission_overwrites'):
			for overwrite in channel['permission_overwrites']:
				self.permission_overwrites.append(PermissionOverwrite(overwrite))

		self.name = test(channel, 'name')
		self.topic = test(channel, 'topic')
		self.nsfw = test(channel, 'nsfw')
		self.last_message_id = test(channel, 'last_message_id')
		self.bitrate = test(channel, 'bitrate')
		self.user_limit = test(channel, 'user_limit')
		self.rate_limit_per_user = test(channel, 'rate_limit_per_user')

		self.recipients: List[User] = []
		if test(channel, 'recipients'):
			for recipient in channel['recipients']:
				self.recipients.append(User(recipient))

		self.icon = test(channel, 'icon')
		self.owner_id = test(channel, 'owner_id')
		self.application_id = test(channel, 'application_id')
		self.parent_id = test(channel, 'parent_id')
		self.last_pin_timestamp = datetime.fromisoformat(channel['timestamp']) if test(channel, 'last_pin_timestamp') else None
		self.rtc_region = test(channel, 'rtc_region')
		self.video_quality_mode = test(channel, 'video_quality_mode')
		self.message_count = test(channel, 'message_count')
		self.member_count = test(channel, 'member_count')

		self.thread_metadata = ThreadMetadata(channel['thread_metadata']) if test(channel, 'thread_metadata') else None
		self.member = ThreadMember(channel['member']) if test(channel, 'member') else None

		self.default_auto_archive_duration = test(channel, 'default_auto_archive_duration')

class StickerItem:
	class Type:
		PNG = 1
		APNG = 2
		LOTTIE = 3

	def __init__(self, item):
		self.id = item['id']
		self.name = item['name']
		self.format_type: self.Type = item['format_type']

class Message:
	def __init__(self, msg):
		self.id = msg['id']
		self.channel_id = msg['channel_id']
		self.guild_id = test(msg, 'guild_id')
		self.author = Member(msg['author'], test(msg, 'member'))
		self.content = msg['content']
		self.timestamp = datetime.fromisoformat(msg['timestamp'])
		self.edited_timestamp = msg['edited_timestamp']
		self.tts = msg['tts']
		self.mention_everyone = msg['mention_everyone']

		self.mentions: List[Member] = []
		for mention in msg['mentions']:
			self.mentions.append(Member(mention, mention['member']))

		self.mention_roles = msg['mention_roles']

		self.mention_channels: List[ChannelMention] = []
		if test(msg, 'mention_channels'):
			for channel in msg['mention_channels']:
				self.mention_roles.append(ChannelMention(channel))

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

		self.nonce = test(msg, 'nonce')
		self.pinned = msg['pinned']
		self.webhook_id = test(msg, 'webhook_id')
		self.type = msg['type']
		self.activity = MessageActivity(msg['activity']) if test(msg, 'activity') else None
		self.application = Application(msg['application']) if test(msg, 'application') else None
		self.application_id = test(msg, 'application_id')
		self.message_reference = MessageReference(msg['message_reference']) if test(msg, 'message_reference') else None
		self.flags = test(msg, 'flags')
		self.referenced_message = Message(msg['referenced_message']) if test(msg, 'referenced_message') else None
		
		self.interaction = MessageInteraction(msg['interaction']) if test(msg, 'interaction') else None

		self.thread = TextChannel(msg['thread']) if test(msg, 'thread') else None

		self.components: List[Component] = []
		if test(msg, 'components'):
			for component in msg['components']:
				self.components.append(Component(component))

		self.sticker_items: List[StickerItem] = []
		if test(msg, 'sticker_items'):
			for sticker_item in msg['sticker_items']:
				self.sticker_items.append(StickerItem(sticker_item))

	def get_reaction(self, emoji: Emoji) -> Reaction:
		for reaction in self.reactions:
			if reaction.emoji == emoji:
				return reaction
