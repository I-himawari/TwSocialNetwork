import pytest
from tinydb import TinyDB, Query, where
import yaml
import os
import tweepy
import os, sys
print(os.getcwd())
sys.path.append(os.getcwd())
from index import *

import itertools


class TestTwitterAPI(object):

    def db_remove_all(self, db):
        db.remove(doc_ids=[v.doc_id for v in db.all()])

    def db_reset(self):
        self.db_remove_all(db_follower)
        self.db_remove_all(db_friend)
        self.db_remove_all(db_like)
        self.db_remove_all(db_user)
        self.db_remove_all(db_tweet)

    def setup_method(self, method):
        self.db_reset()
        self.karin = 968961194257039360  # とりあえず彼の情報を取得時に使う。

    """
    ユーザーの取得・ユーザーのフォロー・フォロワー情報の取得をテストする。
    """
    def test_get_user(self):
        self.db_reset()
        get_user_detail(968961194257039360)
        assert len(db_user.search(where("get_follower_timestamp") == 0)) == 1

        # フォロワー情報を取得する。
        get_user_ff(968961194257039360, follower=True)
        assert len(db_follower.all()) != 0

        # フォロー情報を取得する。
        get_user_ff(968961194257039360, follower=False)
        assert len(db_friend.all()) != 0

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
        db_follower.remove(doc_ids=[v+1 for v in range(len(db_follower.all()))])
        db_friend.remove(doc_ids=[v+1 for v in range(len(db_friend.all()))])
        get_user_detail(968961194257039360)
        db_follower.insert_multiple([{"to": 107736559}, {"to": 953125896822509568}])
        db_friend.insert_multiple([{"to": 968961194257039360}, {"to": 953125896822509568}])
        assert len(diff_ff_table_to_user_table()) == 2

        get_users_detail_in_follower()
        assert len(db_user.all()) == 3

    """
    タイムライン取得関数を動かす。
    """
    def test_get_user_tweet(self):
        get_user_timeline(968961194257039360)
        assert len(db_tweet.all()) != 0

    def test_get_user_like(self):
        get_user_like(968961194257039360)
        assert len(db_like.all()) != 0