"""
validate_examples.py

Validates example JSON files in the repo against the provided JSON-Schemas.
Usage: python validate_examples.py

Installs nothing; requires `jsonschema` package.
"""
import json
import os
import sys
from glob import glob

try:
    from jsonschema import Draft7Validator
except Exception as e:
    print("jsonschema not installed. Install with: python -m pip install jsonschema")
    sys.exit(2)

ROOT = os.path.dirname(__file__)
SCHEMAS = {
    'figure': os.path.join(ROOT, 'Figures', 'figure.schema.json'),
    'dancefloor': os.path.join(ROOT, 'dancefloor.schema.json'),
    'jstree_node': os.path.join(ROOT, 'jstree_node.schema.json'),
}

EXAMPLES = [
    (SCHEMAS['figure'], os.path.join(ROOT, 'Figures', 'Reel_Across_v2.json')),
    (SCHEMAS['figure'], os.path.join(ROOT, 'Dances', 'Marries_Wedding_full_v3.json')),
    (SCHEMAS['dancefloor'], os.path.join(ROOT, 'dancefloor_example.json')),
]


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
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
        # print a compact location and message
        loc = "/" + "/".join([str(p) for p in e.path]) if e.path else "/"
        print(f" - At {loc}: {e.message}")
    return False


def main():
    all_ok = True
    for schema_path, instance_path in EXAMPLES:
        if not os.path.exists(schema_path):
            print(f"Schema missing: {schema_path}")
            all_ok = False
            continue
        if not os.path.exists(instance_path):
            print(f"Example missing: {instance_path}")
            all_ok = False
            continue
        ok = validate_one(schema_path, instance_path)
        all_ok = all_ok and ok
    if all_ok:
        print("\nAll examples validated successfully.")
        sys.exit(0)
    else:
        print("\nValidation failed.")
        sys.exit(1)

if __name__ == '__main__':
    main()
