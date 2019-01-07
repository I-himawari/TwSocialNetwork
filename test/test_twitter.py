import pytest
from tinydb import TinyDB, Query, where
import yaml
import os
import tweepy
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from index import *

import itertools


class TestTwitterAPI(object):

    def db_reset(self):
        db_follower.delete_many({})
        db_friend.delete_many({})
        db_like.delete_many({})
        db_user.delete_many({})
        db_tweet.delete_many({})

    def setup_method(self, method):
        self.db_reset()
        self.karin = 968961194257039360  # とりあえず彼の情報を取得時に使う。

    """
    ユーザーの取得・ユーザーのフォロー・フォロワー情報の取得をテストする。
    """
    def test_get_user(self):
        self.db_reset()
        get_user_detail(968961194257039360)
        assert len(list(db_user.find({"get_follower_timestamp": 0}))) == 1

        # フォロワー情報を取得する。
        get_user_ff(968961194257039360, follower=True)
        assert len(list(db_follower.find())) != 0

        # フォロー情報を取得する。
        get_user_ff(968961194257039360, follower=False)
        assert len(list(db_friend.find())) != 0

    """
    最適なユーザー情報を返すプログラムを検証する。（非DB依存）
    """
    def test_get_valid_user(self):
        self.db_reset()
        db_list = [("0", "0", "0", "0")]
        db_list.extend([v for v in itertools.permutations("0001")])
        db_list.extend([v for v in itertools.permutations("0011")])
        db_list.extend([v for v in itertools.permutations("0111")])
        db_list.extend([("1", "1", "1", "1")])

        db_list = list(set(db_list))

        db_list = [[int(i) for i in v] for v in db_list]

        users_model = list()

        for db_flags in db_list:
            user_model = {
                "id": 1,
                "friends_count": 2000                
            }
            for timestamp, db_flag in zip(TIMESTAMP_LIST, db_flags):
                user_model[timestamp] = db_flag * 100000

            users_model.append(user_model)

        # 関数と同じ条件（未だ取得してない（取得時刻情報がない）情報）に絞り込む。
        users_model_mod = [v for v in users_model if v["get_follower_timestamp"] == 0]
        user_class = sort_user_id_by_score(users_model_mod, "get_follower_timestamp")

        assert user_class["get_follower_timestamp"] == 0
        assert user_class["get_friend_timestamp"] != 0
        assert user_class["get_like_timestamp"] != 0
        assert user_class["get_tweet_timestamp"] != 0

    """
    フォロー・フォロワーより、未だ取得されていないユーザーを取得する。
    """
    def test_lookup_users(self):
        self.db_reset()
        get_user_detail(968961194257039360)
        db_follower.insert_many([{"to": 107736559}, {"to": 953125896822509568}])
        db_friend.insert_many([{"to": 968961194257039360}, {"to": 953125896822509568}])
        assert len(diff_ff_table_to_user_table()) == 2

        get_users_detail_in_follower()
        assert len(list(db_user.find())) == 3

    """
    タイムライン取得関数を動かす。
    """
    def test_get_user_tweet(self):
        get_user_timeline(968961194257039360)
        assert len(list(db_tweet.find())) != 0

    def test_get_user_like(self):
        get_user_like(968961194257039360)
        assert len(list(db_like.find())) != 0

    """
    有効なユーザーを返す。また、MongoDBのUpdateを確認する。
    四騎士関数のテスト。
    """
    def test_valid_user(self):
        self.db_reset()
        users_mock = [{"id": 1}, {"id": 2}]
        for v in TIMESTAMP_LIST:
            for i in range(len(users_mock)):
                users_mock[i][v] = now_timestamp()

        users_mock[1]["get_like_timestamp"] = 0
        db_user.insert_many(users_mock)

        user = get_valid_user("get_like_timestamp")
        assert user["id"] == 2

        db_user.update_one({"id": user["id"]}, {"$set": {"get_like_timestamp": now_timestamp()}})
        user = db_user.find_one({"id": 2})
        assert user["get_like_timestamp"] != 0 
