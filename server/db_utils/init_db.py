from db_declaration import Danmu, LiveStatus, Gift, SuperChat, Captain, View, WatchedChange
from peewee import SqliteDatabase

path = "../db/8792912.db"
#path = "db/22384516.db"

db = SqliteDatabase(path, pragmas=(
            ('cache_size', -1024 * 64),  # 64MB page-cache.
            ('journal_mode', 'wal'))) # Use WAL-mode (you should always use this!).
db.connect()
db.bind([Danmu, LiveStatus, Gift, SuperChat, Captain, View, WatchedChange])
db.create_tables([Danmu, LiveStatus, Gift, SuperChat, Captain, View, WatchedChange])