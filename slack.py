import yaml
import requests
import json

f = open("api-key.yml", "r+")
slack = yaml.load(f)

payload= {
    "username": slack["slack_username"],
    "text": "Pythonよりこんにちは",
    "icon_emoji": slack["slack_icon_emoji"]
}

response = requests.post(slack["slack_url"], json.dumps(payload))