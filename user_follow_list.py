"""
ユーザー同士のフォロー関係を取得する。

フォローID取得
friends/ids

フォロワーID取得
followers/ids

ID→詳細情報取得（100件までの複数）
GET users/lookup

"""
import yaml

f = open("api-key.yml", "r+")
k = yaml.load(f)
