import glob
import json
import os
import sys

from jsonschema import Draft7Validator

ROOT = os.path.dirname(__file__)
SCHEMA_DIR = os.path.join(ROOT, 'Documents', 'Schema')
SCHEMAS = {
    'figure': os.path.join(SCHEMA_DIR, 'figure.schema.json'),
    'dance': os.path.join(SCHEMA_DIR, 'dance.schema.json'),
    'dancefloor': os.path.join(SCHEMA_DIR, 'dancefloor.schema.json'),
    'jstree_node': os.path.join(SCHEMA_DIR, 'jstree_node.schema.json'),
}


def load_json(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def validate_one(schema_path, instance_path):
    schema = load_json(schema_path)
    instance = load_json(instance_path)
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(instance))
    if not errors:
        print(f"OK: {os.path.relpath(instance_path, ROOT)} <-> {os.path.relpath(schema_path, ROOT)}")
        return True
    print(f"FAIL: {os.path.relpath(instance_path, ROOT)} <-> {os.path.relpath(schema_path, ROOT)}")
    for e in errors:
        loc = "/" + "/".join([str(p) for p in e.path]) if e.path else "/"
        print(f" - At {loc}: {e.message}")
    return False


def validate_glob(schema_key, pattern):
    schema_path = SCHEMAS[schema_key]
    files = [p for p in glob.glob(os.path.join(ROOT, pattern), recursive=True) if os.path.basename(p) != os.path.basename(schema_path)]
    ok = True
    for path in files:
        rel = os.path.relpath(path, ROOT)
        if 'subDances' in rel:
            print(f"SKIP: {rel} <-> {os.path.relpath(schema_path, ROOT)} (fragment)")
            continue
        ok = validate_one(schema_path, path) and ok
    return ok


def main():
    all_ok = True
    for schema_path in SCHEMAS.values():
        if not os.path.exists(schema_path):
            print(f"Schema missing: {schema_path}")
            all_ok = False

    all_ok = validate_glob('figure', 'Figures/**/*.json') and all_ok
    all_ok = validate_glob('dance', 'Dances/**/*.json') and all_ok
    if os.path.exists(os.path.join(ROOT, 'dancefloor_example.json')):
        all_ok = validate_one(SCHEMAS['dancefloor'], os.path.join(ROOT, 'dancefloor_example.json')) and all_ok

    if all_ok:
        print("\nAll examples validated successfully.")
        sys.exit(0)
    else:
        print("\nValidation failed.")
        sys.exit(1)


if __name__ == '__main__':
    main()
