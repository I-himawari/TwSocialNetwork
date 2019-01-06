import pytest
import sqlite3
import os, sys
print(os.getcwd())
sys.path.append(os.getcwd())
from sqjson import *
import json

TEST_DB_NAME = "test_db.sqlite3"
def d(dmp):
    return json.dumps(dmp, ensure_ascii=False)

class TestTwitterAPI(object):

    def setup_method(self, method):
        self.db_user = SqliteJson(TEST_DB_NAME, "user_detail")
        self.db_user.reset()

    def test_user_table(self):
        assert self.db_user.table_exist("user_detail")

    def test_insert_table(self):
        self.db_user.reset()
        self.db_user.insert({"abc": 123})
        self.db_user.insert({"abc": 123})
        self.db_user.insert({"abc": 123})
        assert len(self.db_user.all()) == 3

    def test_insert_multiple_table(self):
        self.db_user.reset()
        
        self.db_user.insert_multiple([{"abc": 123}, {"abc": 123}, {"abc": 123}])
        assert len(self.db_user.all()) == 3

    