import os
import dataset

if not os.path.exists('bot.db'):
	print('Welcome to starboard setup.')
	print('You will also need a twitter app, see https://developer.twitter.com/apps.')
	# connect to db and start setting up the bot
	db = dataset.connect('sqlite:///settings.db')

	db.create_table('server')
	db.create_table('ignore_list')
	db.create_table('custom_count')

	print('Your bot\'s token can be obtained from https://discord.com/developers/applications.')
	token = input('Bot token: ')
	db['settings'].insert(dict(name='token', value=token))
	print('For this part you need to open the \'Keys and tokens\' tab of your twitter app.')
	api_key = input('API key: ')
	db['twitter'].insert(dict(name='api_key', value=api_key))
	api_secret = input('API secret key: ')
	db['twitter'].insert(dict(name='api_secret', value=api_secret))
	access_token = input('Access token: ')
	db['twitter'].insert(dict(name='access_token', value=access_token))
	access_token_secret = input('Access token secret: ')
	db['twitter'].insert(dict(name='access_token_secret', value=access_token_secret))

	print('All done, enjoy your starboard.\n')