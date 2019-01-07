# Slackに現在取得したユーザー情報を投げる。
from slack import *
from tinydb import TinyDB, Query, where
from index import *

db_prog = """
UserDetail: %s
Tweet: %s
Like: %s
Friend: %s
Follower: %s
""" % (db_user.count_documents({}), db_tweet.count_documents({}), db_like.count_documents({}), db_friend.count_documents({}), db_follower.count_documents({}))

slack_message(db_prog)