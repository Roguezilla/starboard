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
					embed = Embed(color=0xffcc00, title=title, url=match[0])
					embed.set_image(url=image)
					embed.add_field(name='Original Poster', value=event.author.mention)

					sent: Message = await bot.send_message(event.channel_id, embed=embed.as_json())

					if str(event.channel_id) + str(event.id) in embed_class.cache:
						key = str(sent.channel_id) + str(sent.id)
						# copy original message cache into the new message(our embed) and delete the original message from the cache
						embed_class.cache[key] = embed_class.cache[str(event.channel_id) + str(event.id)]
						del embed_class.cache[str(event.channel_id) + str(event.id)]

						sent.embeds[0].add_field(name='Page', value=f"{embed_class.cache[key]['curr'] + 1}/{len(embed_class.cache[key]['images'])}")
						await bot.edit_message(sent, embed=sent.embeds[0].as_json())
						
						await bot.add_reaction(sent, '⬅️', unicode=True)
						await bot.add_reaction(sent, '➡️', unicode=True)

					# we don't really the message
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

			key = str(event.channel_id)+str(event.message_id)

			# the gallery cache gets wiped when the bot is turned off, so we have to rebuild it
			if key not in embed_class.cache:
				embed_class.build_cache(embed_class.url_data(msg.embeds[0].url), msg, True)
			
			if key in embed_class.cache:			
				gal_size = len(embed_class.cache[key]['images'])
				curr_idx = embed_class.cache[key]['curr']
				
				if str(event.emoji) == '➡️':
					curr_idx = curr_idx + 1 if curr_idx + 1 < gal_size else 0
				else:
					curr_idx = curr_idx - 1 if curr_idx - 1 >= 0 else gal_size - 1

				embed_class.cache[key]['curr'] = curr_idx

				msg.embeds[0].set_image(url=embed_class.cache[key]['images'][curr_idx])
				msg.embeds[0].set_field_at(1, name='Page', value=f"{embed_class.cache[key]['curr'] + 1}/{len(embed_class.cache[key]['images'])}")

				await bot.edit_message(msg, embed=msg.embeds[0].as_json())
				await bot.remove_reaction(msg, event.author, event.emoji)
