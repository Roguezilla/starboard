import os
import dataset

if not os.path.exists('bot.db'):
	print('Welcome to starboard setup.')
	# folder for the logs
	os.makedirs('logs', exist_ok=True)
	# the database itself
	db = dataset.connect('sqlite:///db.db')

	# necessary tables
	db.create_table('server')
	db.create_table('ignore_list')
	db.create_table('custom_count')

	# finally the token
	print('Your bot\'s token can be obtained from https://discord.com/developers/applications.')
	token = input('Token: ')
	db['settings'].insert(dict(name='token', value=token))

	print('All done, enjoy your starboard.')