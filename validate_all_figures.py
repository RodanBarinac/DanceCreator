import json, glob, sys
from jsonschema import Draft7Validator
schema=json.load(open('e:/Git/DanceCreator/simple_figure.schema.json','r',encoding='utf-8'))
validator=Draft7Validator(schema)
files=glob.glob('e:/Git/DanceCreator/Figures/*.json')
if not files:
    print('No figure files found')
    sys.exit(0)
ok_all=True
for f in files:
    instance=json.load(open(f,'r',encoding='utf-8'))
    errors=list(validator.iter_errors(instance))
    rel=f.replace('e:/Git/DanceCreator\\','')
    if not errors:
        print(f'OK: {rel}')
    else:
        ok_all=False
        print(f'FAIL: {rel}')
        for e in errors:
            loc='/'+'/'.join([str(p) for p in e.path]) if e.path else '/'
            print(' - At',loc,':',e.message)
if ok_all:
    print('\nAll Figures valid')
else:
    print('\nSome Figures invalid')
