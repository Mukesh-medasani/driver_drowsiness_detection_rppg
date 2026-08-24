import urllib.request
import time

for i in range(3):
    try:
        with urllib.request.urlopen('http://127.0.0.1:5000/data', timeout=5) as r:
            print('data status', r.status)
            print('data body', r.read(200))
            break
    except Exception as e:
        print('data error', e)
        time.sleep(1)

try:
    req = urllib.request.Request('http://127.0.0.1:5000/video', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = r.read(200)
        print('video bytes', len(data))
        print(data[:80])
except Exception as e:
    print('video error', e)
