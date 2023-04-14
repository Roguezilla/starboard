import os
import dataset

if not os.path.exists('db.db'):
	print('Welcome to starboard setup.')
	db = dataset.connect('sqlite:///db.db')

	db.create_table('server')
	db.create_table('ignore_list')
	db.create_table('custom_count')

	print('Your bot\'s token can be obtained from https://discord.com/developers/applications.')
	token = input('Bot token: ')
	db['settings'].insert(dict(name='token', value=token))

	print('All done, enjoy your starboard.\n')