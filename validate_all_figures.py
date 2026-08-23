import glob
import json
import os
import sys

from jsonschema import Draft7Validator

ROOT = os.path.dirname(__file__)
SCHEMA_PATH = os.path.join(ROOT, 'Documents', 'Schema', 'figure.schema.json')
FIGURES_DIR = os.path.join(ROOT, 'Figures')


def load_json(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def main():
    if not os.path.exists(SCHEMA_PATH):
        print('Schema not found:', SCHEMA_PATH)
        sys.exit(2)

    schema = load_json(SCHEMA_PATH)
    validator = Draft7Validator(schema)
    files = glob.glob(os.path.join(FIGURES_DIR, '**', '*.json'), recursive=True)
    if not files:
        print('No figure files found')
        sys.exit(0)

    ok_all = True
    for f in files:
        if os.path.basename(f) == 'figure.schema.json':
            continue
        instance = load_json(f)
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


if __name__ == '__main__':
    main()
