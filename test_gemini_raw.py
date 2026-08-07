import os, urllib.request, urllib.error, json
from dotenv import load_dotenv

load_dotenv('D:/SparkHub/.env', override=True)
key = os.environ.get('GEMINI_API_KEY')

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
data = json.dumps({"contents":[{"parts":[{"text":"diga oi"}]}]}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'}, method='POST')

try:
    res = urllib.request.urlopen(req)
    print(res.getcode(), res.read().decode())
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode())
