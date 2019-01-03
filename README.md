# TwSocialNetwork
Social network from twitter.


# Playbook
I'm using other web server for getting twitter's data.

Run: ansible-playbook playbook/install.yml -i hosts --ask_become_pass



# Database
I was using TinyDB because simple.


# エラー対処

  * ネットワークが止まった場合→再開するまで中断する。
  * TwitterAPIがエラーを返した→ログをSlackに送信する。
  * Pythonが止まった場合
    * エラーログをSlackに送信する。
    * 取得中のユーザー情報を保存する。

## Slack連携

  * 毎日、0時になったらSlackに取得した総ユーザー数を返す。



