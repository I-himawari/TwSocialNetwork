user_data
purpose: Logging to get detail users data.

ID, user_id(Int), get_follow_time, get_follower_time, get_tweet_time, get_like_time)


user_id(Int) <- -> screen_name(String)
follower/friendのupdateがひとまず終わったり、API待機時間に入ったりしたらまとめて取得する。
Userdataを使う直前、もしくは未取得データが貯まったら（＝定期的に）取得する。

→Userdata取得プログラムは、相対表を呼ぶ時、もしくは1分おきに叩かれる。
→Follower/FriendDBより、まだUserdataに載ってないものを全て取得する。
→APIなどの待機時間になったらdelay=true, getting=falseをする。


get_user_data
1分おきにフォローワー・フレンドを全取得する。また、命令を飛ばされたら即時に実行する。
API制限に入ったらdelay=trueを返す。

内部信号
delay: API制限などに入ってないか。
wakeup: Trueの場合、即時に取得する。
done: 全部取得した場合。

delay, doneになったら、flashフラグを渡す。


follower/friend

{update_time, from, to}


