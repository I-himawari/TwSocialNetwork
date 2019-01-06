from tinydb import TinyDB, Query, where
import yaml
from multiprocessing import Process
from time import sleep
import tweepy
import logging
from datetime import datetime
from slack import slack_message, slack_error_message
import numpy as np
import traceback
import sys
import argparse

# ロギング（API取得情報）のログを保存する。
logging.basicConfig(level=logging.DEBUG, filename="tweet.log", format="%(asctime)s %(levelname)-7s %(message)s")

# 引数に--prodをつけることにより、本番データベースを動かす事が出来る。
parser = argparse.ArgumentParser()
parser.add_argument("--prod", help="If you run own server, this flag mus set", action="store_true")
args = parser.parse_args()

# DB保存先
db_follower_name = "db/follower.json"
db_friend_name = "db/friend.json"
db_like_name = "db/like.json"
db_user_name = "db/user.json"
db_tweet_name = "db/tweet.json"

if not args.prod:
    db_follower_name = "test_" + db_follower_name
    db_friend_name = "test_" + db_friend_name
    db_like_name = "test_" + db_like_name
    db_user_name = "test_" + db_user_name
    db_tweet_name = "test_" + db_tweet_name

# DBの初期化
db_follower = TinyDB(db_follower_name)
db_friend = TinyDB(db_friend_name)
db_like = TinyDB(db_like_name)
db_user = TinyDB(db_user_name)
db_tweet = TinyDB(db_tweet_name)

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

# c = api.user_timeline(968961194257039360, count=200)
# page送ってlen(c)が0になったらend。

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
フォロー・フォロワー・ツイート・Likeなどの詳細情報取得条件より、最も優先すべきユーザーを返す。
1. UserDBをUpdateする。
1. 既存のUserDBにアクセスし、まだ詳細情報を取得していないユーザー一覧を返す。
2. 1件も取得出来なかった場合、詳細情報取得プログラムの問題と判断し、Slackにメッセージを投げ、10分待つ。
3. 1件取得した場合はそのまま返す。
4. 複数件取得した場合は、最適なユーザーを返す関数を通して返す。
"""
def get_valid_user(select_timestamp):
    user_list = db_user.search(where(select_timestamp) == 0)
    get_users_detail_in_follower()

    # 0件もヒットしなかった場合は、Slackに報告し、ランダムにユーザーを取得する。（お気に入りユーザー検索を続ける）。
    if len(user_list) == 0:
        slack_error_message("%s 取得対象ユーザーが1件も見つかりませんでした。" % datetime.now())
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
        return sort_user_id_by_score(user_list, select_timestamp)


"""
ユーザーを指定した条件でソートする。

1. 既に他の情報（例えばフォローならフォロワーとか）の取得情報を確認する（具体的にはtimestampが更新されている（0以外）か）。
他情報が取得されていたら、スコア+1する（優先的に取得する）
2. フォロワー数に応じたスコアを足す。（フォロワー数/2000）
3. 最もスコアが高い（np.argsortの逆（[::-1]）代表値（最初（つまり[0]））を取得する。
"""
def sort_user_id_by_score(user_list, select_timestamp):
    user_arange = np.arange(len(user_list))
    user_score = np.zeros(len(user_arange))
    for t in [v for v in TIMESTAMP_LIST if v != select_timestamp]:
        user_score += np.array([1 if v[t] != 0 else 0 for v in user_list])
    
    user_score += np.array([v["friends_count"] / 2000 for v in user_list])

    return user_list[user_arange[np.argsort(user_score)[::-1][0]]]


"""
follower, friend内で、User詳細情報を取得していないユーザー一覧を取得する。

1. FFTable <- Follower, FriendのDBよりid一覧
2. Usertable <- User詳細情報のDBよりid一覧
3. BeforeTable = FFTable - Usertable
4. GetTable <- BeforeTable.split(per 100)
5. Users.append(TwitterAPI(GetTable))
6. UsersMod <- [AddTimestamp(v) for v in Users]
7. db.insert_multiple(UsersMod)
"""
def diff_ff_table_to_user_table():
    raw_user_list = [v["to"] for v in db_follower.all()]
    raw_user_list.extend([v["to"] for v in db_friend.all()])
    
    # Usertable <- User詳細情報のDBよりid一覧
    db_user_list = [v["id"] for v in db_user.all()]
    
    return list(set(raw_user_list) - set(db_user_list))


"""
未だ取得していないユーザーの詳細情報を取得する。
:return: bool API制限などで全ての情報が取得出来ない場合にFalseを返す。
"""
def get_users_detail_in_follower():
    before_table = diff_ff_table_to_user_table()
    if len(before_table) == 0:
        return True
    # FFTable <- Follower, FriendのDBよりid一覧
    # Fromは詳細情報の存在が確定しているのでToより選択する。

    table_count = 0
    users = list()

    # Pythonの[]表記は、[開始:終点-1]。
    while(True):
        end_point = min(table_count + 100, len(before_table))
        try:
            users_api = api.lookup_users(before_table[table_count:end_point])
        except tweepy.RateLimitError:
            return False
        except tweepy.TweepError:
            slack_error_message(traceback.format_exc())
            return False

        users.extend(api.lookup_users(before_table[table_count:end_point]))

        # 取得したいユーザー名一覧を座標が超えていたら終了。そうでなければ座標を100（取得数）ずらす。
        if table_count + 100 > end_point:
            # tweepyのuserオブジェクト（戻り値）はそのままでは加工出来ない為、dictに変換する（ややこしい）
            users_dict = [v._json for v in users]
            set_users_detail(users_dict)
            return
        else:
            table_count += 100

    return True
    

def lookup_users():
    return api.lookup_users(screen_names=["vxtuberkarin", "factor_null"])

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
tweepyのユーザーオブジェクトをDBに格納する。（ついでに、ツイートなどの取得情報もつける）
"""
def set_users_detail(users_object):
    for i in range(len(users_object)):
        for timestamp in TIMESTAMP_LIST:
            users_object[i][timestamp] = 0
    db_user.insert_multiple(users_object)


"""
指定したユーザーIDの詳細情報（プロフィールなど）を返す。
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
指定したユーザーのツイートもしくはLikeを取得し、DBに格納する。
"""
def get_user_action(user_id, page=1, tweet=True):
    try:
        select_function = api.user_timeline if tweet else api.favorites
        c = select_function(user_id=user_id, count=200, page=page)

        if len(c) == 0:
            return

        c_modify = [v._json for v in c]

        db = db_tweet if tweet else db_like
        db.insert_multiple(c_modify)
            
        get_user_action(user_id, page+1, tweet=tweet)

    except tweepy.RateLimitError:
        logging.info("[UserTweet] Stop Iteration, process complete")
        slack_message("[%s] ツイート取得の上限に達しました" % "Timeline" if tweet else "Like")
        sleep(60 * 15)
        get_user_action(user_id, page, tweet=tweet)

    except tweepy.TweepError:
        slack_error_message(traceback.format_exc())
        return


# ユーザーのツイートを取得する。
def get_user_timeline(user_id, page=1):
    get_user_action(user_id, page, tweet=True)


# ユーザーの好みを取得する。
def get_user_like(user_id, page=1):
    get_user_action(user_id, page, tweet=False)


# ----------------------------------------- 四騎士関数 -----------------------------------------
# 取得すべき最適なユーザー情報を返し、実行を繰り返す。
def four_knight_user_like():
    print("START USER LIKE")
    while True:
        get_user_like(get_valid_user("get_like_timestamp"))
    

def four_knight_user_timeline():
    print("START USER TIMELINE")
    while True:
        get_user_timeline(get_valid_user("get_tweet_timestamp"))
    

def four_knight_user_friend():
    print("START USER FRIEND")
    while True:
        get_user_ff(get_valid_user("get_friend_timestamp"), follower=False)
    

def four_knight_user_follower():
    print("START USER FOLLOWER")
    while True:
        get_user_ff(get_valid_user("get_follower_timestamp"), follower=True)
    



"""
1. 最初の1ユーザー情報をDBに格納する。（取得条件が見つからないパターンを防ぐ為）
2. フォロー・フォロワー・ツイート・Like（以降四騎士）を取得する関数を実行する。

四騎士関数（以降をループする）
1. 最も取得すべきユーザー情報を返す。
2. そのユーザーの四騎士などを片っ端から取得する。
3. 取得し終わるorAPI制限に入ったりした時に、friend/followの詳細情報を取得する。
4. 全て取得したらループする。
"""
def runner():
    get_user_detail(968961194257039360)
    Process(target=four_knight_user_like).start()
    Process(target=four_knight_user_timeline).start()
    Process(target=four_knight_user_friend).start()
    Process(target=four_knight_user_follower).start()

    # get_user_detailのループを行う。最終動作より5分が経過したら実行させる。
    while True:
        sleep(600)
        get_users_detail_in_follower()

if __name__ == "__main__":
    print("MAIN")
    runner()