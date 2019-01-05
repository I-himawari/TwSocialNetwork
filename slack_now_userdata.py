# Slackに現在取得したユーザー情報を投げる。
import slack
from tinydb import TinyDB, Query, where
from index import *

db_prog = """
UserDetail: %s
Tweet: %s
Like: %s
Friend: %s
Follower: %s
""" % (len(db_user.all()), len(db_tweet.all()), len(db_like.all()), len(db_friend.all()), len(db_follower.all()))

slack_message(db_prog)