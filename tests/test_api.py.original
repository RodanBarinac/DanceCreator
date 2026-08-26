#!/usr/bin/env python3
import urllib.request
import json

try:
    r = urllib.request.urlopen('http://127.0.0.1:5000/api/figures')
    data = json.loads(r.read().decode())
    print(f'{len(data)} figures')
    if data:
        print('First figure:', json.dumps(data[0], indent=2))
    else:
        print('EMPTY - no figures returned')
except Exception as e:
    print(f'Error: {e}')
