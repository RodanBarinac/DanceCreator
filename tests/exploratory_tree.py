import urllib.request, json
r = urllib.request.urlopen('http://127.0.0.1:5000/api/dances/Marries_Wedding_full_v3')
data = json.loads(r.read().decode())
tree = data['tree']
print('Root:', tree['id'], tree['text'])
print('Children count:', len(tree['children']))
for i, child in enumerate(tree['children'][:5]):
    print(f"  [{i}] {child['text']}: {len(child.get('children', []))} children, type={child.get('data', {}).get('type')}")
    if child.get('children'):
        for j, subchild in enumerate(child['children'][:2]):
            print(f"      [{j}] {subchild['text']}")
