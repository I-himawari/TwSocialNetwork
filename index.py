from tinydb import TinyDB, Query, where
import yaml
import multiprocessing
from multiprocessing import Value
from time import sleep
import tweepy
import logging
from datetime import datetime
from slack import slack_message, slack_error_message
import numpy as np


datetime.now()

logging.basicConfig(level=logging.DEBUG, filename="tweet.log", format="%(asctime)s %(levelname)-7s %(message)s")

db_follower_name = "db/follower.json"
db_friend_name = "db/friend.json"
db_like_name = "db/like.json"
db_user_name = "db/user.json"
db_tweet_name = "db/tweet.json"
db_follower = TinyDB(db_follower_name)
db_friend = TinyDB(db_friend_name)
db_like = TinyDB(db_like_name)
db_user = TinyDB(db_user_name)
db_tweet = TinyDB(db_tweet_name)
db_query = Query()

f = open("api-key.yml", "r+")
key = yaml.load(f)
auth = tweepy.OAuthHandler(key["consumer_key"], key["consumer_secret"])
auth.set_access_token(key["access_token"], key["access_token_secret"])

api = tweepy.API(auth)


TIMESTAMP_LIST = ["get_follower_timestamp", "get_friend_timestamp", "get_like_timestamp", "get_tweet_timestamp"]

# 現在のtimestampを返す。
def now_timestamp():
    return int(datetime.now().timestamp())


# DBにfrom_toの形のデータを入れる（つまりフォロー情報など）
def db_insert_from_to(_db, _from, _to):
    _db.insert(db_insert_param(_db, _from, _to))

# from_toの形のデータをDB用に変換する。
def db_insert_param(_db, _from, _to):
    return {"time": now_timestamp(), "from": _from, "to": _to}


def get_tweets(process_name, cursor):
    """
    Friend, Follower関連のカーソル（自動的に次のものを取得する機能）の例外処理。
    Generator used to retrieve tweets from the user
    :return:
    """
    while True:
        try:
            yield cursor.next()
        except tweepy.RateLimitError:
            logging.info("[%s] Timeout Reached, Sleep for 15 minutes before restart" % process_name)
            sleep(15 * 60)
            logging.info("[%s] Waking up. Try again" % process_name)
        except StopIteration:
            logging.info("[%s] Stop Iteration, process complete" % process_name)
            break
        except Exception as e:
            logging.info("[%s] Generic Error, restart in 60 seconds: %s" % (process_name, e))
            sleep(60) 

"""
クラス作るよりdefで組んだ方が手早いし確実だった。
"""

"""
詳細情報を取得したいユーザー情報を返す。
1. 既存の詳細情報取得テーブルに、まだ取得してないユーザーを確認する。
2. 取得していないユーザーがテーブルにない場合、User情報が格納されたDBよりユーザーを捻出する。
3. 既存のDBが存在しない場合は、ランダムにユーザーIDを指定する。（フォロー・フォローワー関係図→Slackで求める。

フォロー、フォロワーの関連が最も多く、なおかつまだ取得されていないユーザー。

フォローされている数で取得する。何故ならば、価値のあるユーザー尺度としてはかなり優秀だから。
　　取得したユーザーによるフォロー数で、上位を抽出。
user <- follower_table_sort_follower_max
user <- user.user_table_sort_follower_max
user <- user.random
"""
def get_valid_user(select_timestamp):
    user_list = db_user.search(where(select_timestamp) == 0)

    # 0件もヒットしなかった場合は、Slackに報告し、ランダムにユーザーを取得する。（お気に入りユーザー検索を続ける）。
    if len(user_list) == 0:
        slack_error_message("取得対象ユーザーが1件も見つかりませんでした。")
        sleep(600)
        get_valid_user(select_timestamp)

    # 1件ヒットの場合は、取得したユーザーを返す。
    elif len(user_list) == 1:
        return user_list[0]

    # 2件以上ヒットの場合は、以下の処理を行う。
    # 1. 取得したユーザーごとの得点テーブルを作る。
    # 2. 他のselect_timestampが0以外（つまり計算されている）場合、スコアを+1する。
    # 3. フォロワー数 / 2000をスコアに足す。
    # 4. 最もスコアの多いユーザーを返す。
    else:
        # ユーザーIDと得点の相対表を作っておく。

        # 使い慣れてるという理由でnumpy使ってるけど、割と必要性ないと思う。
        user_id_list = np.array([v["id"] for v in user_list])
        user_score = np.zeros(len(user_id_list))
        for t in TIMESTAMP_LIST:
            user_score += np.array([1 if v[t] != 0 else 0 for v in user_list])
        
        user_score += np.array([v["friends_count"] / 2000 for v in user_list])

        return user_id_list[np.argsort(user_score)][0]

"""
follower, friend内で、なおかつ詳細情報を取得していないユーザーの詳細を取得する。

1. ユーザー詳細情報を取得したユーザーID一覧を取得する。
2. follower, friendのuser_idテーブルを取得する。
"""
def get_users_detail_in_follower():
    pass



"""
スクリーン名をユーザーIDに変換する。

1. UserDBよりスクリーン名で検索する。
2. 存在しなかった場合は新しく取得する。
"""
def screen_name_to_user_id(screen_name):
    user = db_user.search(where("screen_name") == screen_name)
    if len(user) == 0:
        get_user_detail(screen_name)
        screen_name_to_user_id(screen_name)
    return user[0]["id"]


"""
ユーザーオブジェクト情報にフォロー関連取得フラグ（Timestampと同一とする）を入れ、DBに格納する。
"""
def set_user_detail(user_object):
    for timestamp in TIMESTAMP_LIST:
        user_object[timestamp] = 0
    db_user.insert(user_object)


"""
1人のユーザーのフォロー情報を取得する。
"""
def get_user_detail(username):
    u = api.get_user(username)._json
    set_user_detail(u)


"""
指定したユーザーのフォロー・フォロワー情報を取得する。
folloer TrueならFollower、FalseならFriendを取得する。
"""
def get_user_ff(user_id, follower=True):
    if follower:
        logger_flag = "Follower"
        api_name = api.followers_ids
        db_name = db_follower
    else:
        logger_flag = "Friend"
        api_name = api.friends_ids
        db_name = db_friend
    c = get_tweets(logger_flag, tweepy.Cursor(api_name, user_id).items())
    l = list()
    for p in c:
        l.append(db_insert_param(db_name, user_id, p))

    db_name.insert_multiple(l)


"""
5つのTwitter APIを制御する。
get_user_friend, get_user_follower:
get_user_like:
get_user_tweet: この辺りは回しっぱ。

get_user_detail: デフォルトでは最終動作より5分経過、あるいは叩かれたら（動作フラグがTになったら）動かす。
"""
def runner():
    wakeup = Value("c_bool", False)  # get_user_detailを動かす為の信号。Trueにしたら動く。user_data_doneがTrueになったのを確認したら、Falseにして戻る。
    user_data_done = Value("c_bool", False)  # ユーザー詳細データがAPI待機もしくは完全に取得したらTrueにし、

    # get_user_detailのループを行う。最終動作より5分が経過したら実行させる。
    while True:
        sleep(100)
    pass

"""
TwitterのAPIを指定した時間おきに取得する

最初の1ユーザーを指定する。
ユーザーの詳細情報（フォロー、フォロワー、ツイート、Like）を取得する。
フォロー、フォロワーテーブルより、アルゴリズム（既存のユーザーと繋がってる数）に従い次に詳細情報を取得したいユーザーを返す。
フォロー・フォロワー・ツイート・Likeは別々に計算する為、どれかが早く終わる事がある→1つでも早く終わったら、早めに次のユーザーを返す？（取得結果ごとに候補ユーザーがずれる可能性がある為、候補ユーザーリストを保管する場所が必要と考える。）
    Python保存：簡単だが、取得ログの保存が出来ない。
    TinyDB保存（ID, user_id, date(per f, fw, tw, like))：まあ良いと思う。完了したらそれぞれの更新日時をinsertする。Datetime型がないのでTimestampで記録することになる。

基本的にユーザーの取得はuser_id（Twitter側で振られる数字ナンバーのことで、表示されるIDとは独立）の方が望ましい。
get_first_user

仕様上、複雑に単一プロセスで管理するより、マルチプロセスで動かした方が楽。
"""
