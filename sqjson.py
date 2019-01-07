import sqlite3
import json

class SqliteJson(object):

    """
    指定したDB名（ファイル名）の指定したテーブル名に接続する。
    テーブルが存在しなかった場合は作る。
    """
    def __init__(self, db_name, table_name):
        conn = sqlite3.connect(db_name)
        self.commit = conn.commit
        self.table_name = table_name
        self.c = conn.cursor()
        if not self.table_exist():
            self.c.execute("create table %s(id integer primary key, json json)" % table_name)
            self.commit()

    def d(self, dict_param):
        return json.dumps(dict_param, ensure_ascii=False)
    """
    テーブルの存在を確認する。存在するならTrueを返す。
    """
    def table_exist(self, table_name=False):
        if not table_name:
            table_name = self.table_name

        col = list(self.c.execute("SELECT name FROM sqlite_master WHERE type='table';"))
        col_sort = [v for v in col if v[0] == table_name]
        if len(col_sort) != 0:
            return True
        else:
            return False

    def where(self):
        """
        指定した条件で絞り込みする。
        今回は別に使わないので実装しない。
        """
        pass
    
    def insert(self, v):
        """
        1つだけtableに挿入する。
        """
        print(self.d(v))
        self.c.execute("insert into %s(json) values('%s')" % (self.table_name, self.d(v)))
        self.commit()

    def insert_multiple(self, v_list):
        """
        複数情報をtableに挿入する。
        """
        """
        l = ["('%s')," % self.d(v) for v in v_list]
        l = "".join(l)
        l = l[:-1] 
        self.c.execute("insert into %s(json) values %s" % (self.table_name, l))
        self.commit()
        """
        for v in v_list:
            self.insert(v)

    def reset(self):
        """
        tableに格納されている全てのデータを削除する。
        """
        self.c.execute("delete from %s" % self.table_name)
        self.commit()

    def select_pre(self, param):
        """
        データを取得した後の処理（使う前の処理）を行う。例えばtupleをjsonに変換したり。
        """
        return [json.loads(v[0]) for v in list(param)]

    def all(self):
        """
        全てのJSON情報を返す
        """
        return self.select_pre(self.c.execute("select json from %s" % self.table_name))

    def search(self, where, equal):
        """
        JSONの検索結果を返す（whereがjson内の指定する要素、equalが取得する等価のオブジェクト（等価以外も出来るけど今の所はこれでやってる）
        """
        return self.select_pre(self.c.execute("select %s.json from %s, json_each(%s.json,'$.%s') where json_each.value == %s" % (self.table_name, self.table_name, self.table_name, where, equal)))
