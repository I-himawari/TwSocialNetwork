from tinydb import TinyDB, Query
import yaml


class TwitterAPIReader(object):

    def __init__(self):
        self.user = TinyDB('db/user.json')
        self.follow = TinyDB('db/follow.json')
        self.follower = TinyDB('db/follower.json')
        self.tweet = TinyDB('db/user.json')
        self.q = Query()
        f = open("api-key.yml", "r+")
        self.key = yaml.load(f)

    def run(self):

        """
        
        TwitterのAPIを指定した時間おきに取得する
        """