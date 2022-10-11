import re

from db import BotDB
from discpy.discpy import DiscPy
from discpy.events import ReactionAddEvent
from discpy.message import Embed, Message

from cogs.custom_embed_types.instagram import Instagram
from cogs.custom_embed_types.reddit import Reddit


class CustomEmbeds(DiscPy.Cog):
	def __init__(self, bot: DiscPy):
		@bot.event(self)
		async def on_message(event: Message):
			if event.author.bot or not BotDB.is_setup(event.guild_id):
				return

			if match := re.findall(f"{Instagram.regex()}|{Reddit.regex()}", event.content):
				match = tuple(filter(lambda x: x != '', match[0]))

				if 'instagram' == match[1]: embed_class = Instagram
				elif 'redd' == match[1]: embed_class = Reddit

				image, title = embed_class.return_link(match[0], event)
				if image and title:
					embed = Embed(color=0xffcc00, title=title, description=f'[Jump directly to {embed_class.str()}]({match[0]})')
					embed.set_image(url=image)
					embed.add_field(name='Sender', value=event.author.mention)

					sent: Message = await bot.send_message(event.channel_id, embed=embed.as_json())

					if str(event.channel_id) + str(event.id) in embed_class.gallery_cache:
						# copy old message info into the new message(our embed) and delete old message from the dictionary
						embed_class.gallery_cache[str(sent.channel_id) + str(sent.id)] = embed_class.gallery_cache[str(event.channel_id) + str(event.id)]
						del embed_class.gallery_cache[str(event.channel_id) + str(event.id)]

						embed: Embed = sent.embeds[0]
						embed.add_field(name='Page', value=f"{embed_class.gallery_cache[str(sent.channel_id) + str(sent.id)]['curr']}/{embed_class.gallery_cache[str(sent.channel_id) + str(sent.id)]['size']}", inline=True)
						await bot.edit_message(sent, embed=embed.as_json())
						
						await bot.add_reaction(sent, '⬅️', unicode=True)
						await bot.add_reaction(sent, '➡️', unicode=True)

					# we don't really the message and it only occupies space now
					await bot.delete_message(event)

		@bot.event(self)
		async def on_reaction_add(event: ReactionAddEvent):
			# return if the payload author is the bot or if the payload emote is wrong
			if event.author.bot or not any(e == str(event.emoji) for e in ['➡️', '⬅️']):
				return

			msg: Message = await bot.fetch_message(event.channel_id, event.message_id)
				
			# return if the reacted to message isn't by the bot or if the embed isn't valid
			if msg.author.id != bot.me.user.id:
				return

			if Instagram.validate_embed(msg.embeds): embed_class = Instagram
			elif Reddit.validate_embed(msg.embeds): embed_class = Reddit
			else: return

			msg_id = str(event.channel_id)+str(event.message_id)

			# we want to repopulate the cache when the bot is restarted
			if msg_id not in embed_class.gallery_cache:
				url = re.findall(f"\[Jump directly to {embed_class.str()}\]\((.+)\)", msg.embeds[0].description)
				# see populate_cache
				if embed_class.populate_cache(embed_class.url_data(url[0]), msg, True) == 0:
					return
			
			if msg_id in embed_class.gallery_cache:
				embed: Embed = msg.embeds[0]

				await embed_class.fix_embed_if_needed(bot, msg_id, msg)
					
				gal_size = embed_class.gallery_cache[msg_id]['size']
				curr_idx = embed_class.gallery_cache[msg_id]['curr']
				
				if str(event.emoji) == '➡️':
					curr_idx = curr_idx + 1 if curr_idx + 1 <= gal_size else 1
				else:
					curr_idx = curr_idx - 1 if curr_idx - 1 >= 1 else gal_size

				embed_class.gallery_cache[msg_id]['curr'] = curr_idx
				new_url = embed_class.gallery_cache[msg_id][curr_idx]

				embed.set_image(url=new_url)
				embed.set_field_at(1, name='Page', value=f"{embed_class.gallery_cache[str(msg.channel_id) + str(msg.id)]['curr']}/{embed_class.gallery_cache[str(msg.channel_id) + str(msg.id)]['size']}")

				await bot.edit_message(msg, embed=embed.as_json())
				await bot.remove_reaction(msg, event.author, event.emoji)
