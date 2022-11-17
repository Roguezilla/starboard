import dataset

class BotDB:
    conn: dataset.Database = None

    @staticmethod
    def connect(db = 'sqlite:///db.db'):
        BotDB.conn = dataset.connect(db)

    @staticmethod
    def find_server(guild_id):
        return BotDB.conn['server'].find_one(server_id = guild_id)

    @staticmethod
    def is_setup(guild_id):
        return BotDB.find_server(guild_id) is not None

    @staticmethod
    def in_ignore_list(server_id, channel_id, msg_id):
        return BotDB.conn['ignore_list'].find_one(server_id = server_id, channel_id = channel_id, message_id = msg_id)

    @staticmethod
    def get_custom_count(server_id, channel_id):
        return BotDB.conn['custom_count'].find_one(server_id = server_id, channel_id = channel_id)
    
    @staticmethod
    def get_token():
        return BotDB.conn['settings'].find_one(name='token')['value']