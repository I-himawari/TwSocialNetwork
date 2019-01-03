import pytest
from tinydb import TinyDB, Query, where
import yaml
import os
import tweepy
import os, sys
print(os.getcwd())
sys.path.append(os.getcwd())
from index import *

def rm(file_name):
    try:
        os.remove(file_name)
    except OSError:
        pass

class TestTwitterAPI(object):

    def setup_method(self, method):
        rm(db_follower_name)
        rm(db_friend_name)
        rm(db_like_name)
        rm(db_user_name)
        rm(db_tweet_name)

    def teardown_method(self, method):
        rm(db_follower_name)
        rm(db_friend_name)
        rm(db_like_name)
        rm(db_user_name)
        rm(db_tweet_name)

    def test_get_user(self):
        """
        前準備として、あるuser情報を格納する。
        """
        get_user_detail("vxtuberkarin")
        assert len(db_user.search(where("get_follower_timestamp") == 0)) == 1

        # フォロワー情報を取得する。
        get_user_ff("vxtuberkarin", follower=True)
        assert len(db_follower.all()) != 0

        # フォロー情報を取得する。
        get_user_ff("vxtuberkarin", follower=False)
        assert len(db_friend.all()) != 0