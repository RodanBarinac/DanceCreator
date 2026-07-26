import json, glob, sys, os
from jsonschema import Draft7Validator
ROOT = os.path.dirname(__file__)
schema_path = os.path.join(ROOT, 'Figures', 'figure.schema.json')
if not os.path.exists(schema_path):
    print('Schema not found:', schema_path)
    sys.exit(2)
schema = json.load(open(schema_path, 'r', encoding='utf-8'))
validator = Draft7Validator(schema)
files = glob.glob(os.path.join(ROOT, 'Figures', '*.json'))
if not files:
    print('No figure files found')
    sys.exit(0)
ok_all = True
for f in files:
    if os.path.basename(f) == 'figure.schema.json':
        continue
    instance = json.load(open(f, 'r', encoding='utf-8'))
    errors = list(validator.iter_errors(instance))
    rel = os.path.relpath(f, ROOT)
    if not errors:
        print(f'OK: {rel}')
    else:
        ok_all = False
        print(f'FAIL: {rel}')
        for e in errors:
            loc = '/' + '/'.join([str(p) for p in e.path]) if e.path else '/'
            print(' - At', loc + ':', e.message)
if ok_all:
    print('\nAll Figures valid against figure.schema.json')
    sys.exit(0)
else:
    print('\nSome Figures invalid')
    sys.exit(1)
