import yaml
import requests
import json
from datetime import datetime
import sys
import traceback

f = open("api-key.yml", "r+")
slack = yaml.load(f)

def slack_error_message(message):
    slack_message(message, error=True)


def slack_message(message, error=False):
    payload = {
        "username": slack["slack_username"],
        "text": "[%s] %s" % (datetime.now() , message),
        "icon_emoji": slack["slack_icon_emoji"]
    }

    if error:
        payload["channel"] = "#server-error"

    requests.post(slack["slack_url"], json.dumps(payload))


def myexcepthook(type, value, tb):
    tbtext = ''.join(traceback.format_exception(type, value, tb))
    
    sys.stderr.write(tbtext)
    slack_error_message(tbtext)


sys.excepthook = myexcepthook