import glob
import json
import os
import sys

from jsonschema import Draft7Validator

ROOT = os.path.dirname(__file__)
SCHEMA_PATH = os.path.join(ROOT, 'Documents', 'Schema', 'dance.schema.json')
DANCES_DIR = os.path.join(ROOT, 'Dances')


def load_json(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def main():
    if not os.path.exists(SCHEMA_PATH):
        print('Schema not found:', SCHEMA_PATH)
        sys.exit(2)

    schema = load_json(SCHEMA_PATH)
    validator = Draft7Validator(schema)
    files = glob.glob(os.path.join(DANCES_DIR, '**', '*.json'), recursive=True)
    if not files:
        print('No dance files found')
        sys.exit(0)

    ok_all = True
    for f in files:
        rel = os.path.relpath(f, ROOT)
        if 'subDances' in rel:
            print(f'SKIP: {rel} (fragment)')
            continue
        instance = load_json(f)
        errors = list(validator.iter_errors(instance))
        if not errors:
            print(f'OK: {rel}')
        else:
            ok_all = False
            print(f'FAIL: {rel}')
            for e in errors:
                loc = '/' + '/'.join([str(p) for p in e.path]) if e.path else '/'
                print(' - At', loc + ':', e.message)
    if ok_all:
        print('\nAll Dances valid against dance.schema.json')
        sys.exit(0)
    else:
        print('\nSome Dances invalid')
        sys.exit(1)


if __name__ == '__main__':
    main()
