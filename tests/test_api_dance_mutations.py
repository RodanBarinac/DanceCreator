import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import GUI_DanceCreator_App as app_module
from src.engine.persistence.FileManager import FileManager


def make_dance_payload(name="Existing Dance"):
    return {
        "Name": name,
        "Desc": f"{name} description",
        "shape": "3/32",
        "FigureList": [
            "s",
            [
                [[1, 1], ["H1DR", []]],
                [[2, 1], ["1cWait", []]],
            ],
        ],
        "Version": 3,
    }


def make_tree_payload(figure_name="1cRT"):
    return {
        "tree": {
            "id": "root",
            "text": "Existing Dance",
            "type": "root",
            "data": {},
            "children": [
                {
                    "id": "group-1",
                    "text": "Series",
                    "type": "group",
                    "data": {"groupType": "s"},
                    "children": [
                        {
                            "id": "figure-1",
                            "text": figure_name,
                            "type": "figure",
                            "data": {
                                "figureName": figure_name,
                                "anchor": [1, 1],
                                "addons": [],
                            },
                            "children": [],
                        }
                    ],
                }
            ],
        }
    }


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def client_and_dances_dir(tmp_path, monkeypatch):
    dances_dir = tmp_path / "Dances"
    dances_dir.mkdir()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dances_dir))

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client, dances_dir


class TestPutDanceEndpoint:
    def test_put_dance_updates_file_on_disk(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        dance_path = dances_dir / "Existing Dance.json"
        write_json(dance_path, make_dance_payload())

        payload = make_dance_payload("Updated Dance")
        payload["Desc"] = "Updated description"

        response = client.put(f"/api/dances/{quote('Existing Dance.json', safe='')}", json=payload)

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "ok"
        assert body["message"] == "Dance updated"
        assert body["file"] == "Existing Dance.json"
        assert body["dance"]["Name"] == "Updated Dance"
        assert body["dance"]["Version"] == 3
        assert body["dance"]["shape"] == "3/32"

        saved = read_json(dance_path)
        assert saved["Name"] == "Updated Dance"
        assert saved["Desc"] == "Updated description"

    def test_put_dance_returns_400_for_validation_error(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        write_json(dances_dir / "Existing Dance.json", make_dance_payload())

        payload = make_dance_payload()
        del payload["Desc"]

        response = client.put(f"/api/dances/{quote('Existing Dance.json', safe='')}", json=payload)

        assert response.status_code == 400
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "validation_error"
        assert body["field"] == "Desc"

    def test_put_dance_returns_404_for_missing_file(self, client_and_dances_dir):
        client, _ = client_and_dances_dir

        response = client.put(f"/api/dances/{quote('Missing Dance.json', safe='')}", json=make_dance_payload())

        assert response.status_code == 404
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "not_found"

    def test_put_dance_returns_400_for_malformed_json_body(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        write_json(dances_dir / "Existing Dance.json", make_dance_payload())

        response = client.put(
            f"/api/dances/{quote('Existing Dance.json', safe='')}",
            data='{"Name": "Broken"',
            content_type="application/json",
        )

        assert response.status_code == 400
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "validation_error"
        assert body["field"] == "body"

    def test_put_dance_returns_409_when_expected_hash_conflicts(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        dance_path = dances_dir / "Existing Dance.json"
        write_json(dance_path, make_dance_payload())

        payload = make_dance_payload("Updated Dance")
        payload["_expected_hash"] = "not-the-current-hash"

        response = client.put(f"/api/dances/{quote('Existing Dance.json', safe='')}", json=payload)

        assert response.status_code == 409
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "conflict"
        assert read_json(dance_path)["Name"] == "Existing Dance"

    def test_put_dance_accepts_matching_expected_hash(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        dance_path = dances_dir / "Existing Dance.json"
        write_json(dance_path, make_dance_payload())
        expected_hash = FileManager.compute_file_hash(str(dance_path))

        payload = make_dance_payload("Hash Matched Dance")
        payload["_expected_hash"] = expected_hash

        response = client.put(f"/api/dances/{quote('Existing Dance.json', safe='')}", json=payload)

        assert response.status_code == 200
        assert read_json(dance_path)["Name"] == "Hash Matched Dance"

    def test_put_dance_removes_expected_hash_before_persisting(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        dance_path = dances_dir / "Existing Dance.json"
        write_json(dance_path, make_dance_payload())
        expected_hash = FileManager.compute_file_hash(str(dance_path))

        payload = make_dance_payload()
        payload["_expected_hash"] = expected_hash

        response = client.put(f"/api/dances/{quote('Existing Dance.json', safe='')}", json=payload)

        assert response.status_code == 200
        assert "_expected_hash" not in read_json(dance_path)


class TestPostDanceEndpoint:
    def test_post_dance_creates_new_file(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        payload = make_dance_payload("Brand New Dance")

        response = client.post("/api/dances", json=payload)

        assert response.status_code == 201
        body = response.get_json()
        assert body["status"] == "ok"
        assert body["message"] == "Dance created"
        assert body["file"] == "Brand New Dance.json"
        created_path = dances_dir / "Brand New Dance.json"
        assert created_path.exists()
        assert read_json(created_path)["Name"] == "Brand New Dance"

    def test_post_dance_rejects_duplicate_name(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        write_json(dances_dir / "Brand New Dance.json", make_dance_payload("Brand New Dance"))

        response = client.post("/api/dances", json=make_dance_payload("Brand New Dance"))

        assert response.status_code == 409
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "conflict"

    def test_post_dance_returns_400_for_missing_required_field(self, client_and_dances_dir):
        client, _ = client_and_dances_dir
        payload = make_dance_payload("Incomplete Dance")
        del payload["FigureList"]

        response = client.post("/api/dances", json=payload)

        assert response.status_code == 400
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "validation_error"
        assert body["field"] == "FigureList"

    def test_post_dance_returns_400_for_non_object_body(self, client_and_dances_dir):
        client, _ = client_and_dances_dir

        response = client.post("/api/dances", json=["not", "an", "object"])

        assert response.status_code == 400
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "validation_error"
        assert body["field"] == "body"

    def test_post_dance_sanitizes_unsafe_name_into_safe_filename(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        payload = make_dance_payload("..\\Unsafe/ Dance:*?")

        response = client.post("/api/dances", json=payload)

        assert response.status_code == 201
        body = response.get_json()
        assert body["file"].endswith(".json")
        assert ".." not in body["file"]
        assert "/" not in body["file"]
        assert "\\" not in body["file"]
        assert (dances_dir / body["file"]).exists()

    def test_post_dance_does_not_create_backup_for_new_file(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir

        response = client.post("/api/dances", json=make_dance_payload("No Backup Dance"))

        assert response.status_code == 201
        assert not list(dances_dir.glob("No Backup Dance.json.*.bak"))

    def test_post_dance_response_contains_minimal_summary(self, client_and_dances_dir):
        client, _ = client_and_dances_dir

        response = client.post("/api/dances", json=make_dance_payload("Summary Dance"))

        body = response.get_json()
        assert body["dance"] == {
            "Name": "Summary Dance",
            "Version": 3,
            "shape": "3/32",
        }


class TestPutDanceTreeEndpoint:
    def test_put_dance_tree_updates_figure_list_and_preserves_metadata(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        dance_path = dances_dir / "Existing Dance.json"
        original = make_dance_payload()
        write_json(dance_path, original)

        response = client.put(
            f"/api/dances/{quote('Existing Dance.json', safe='')}/tree",
            json=make_tree_payload("1cRT"),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "ok"
        assert body["message"] == "Dance tree updated"
        assert body["file"] == "Existing Dance.json"

        saved = read_json(dance_path)
        assert saved["Name"] == original["Name"]
        assert saved["Desc"] == original["Desc"]
        assert saved["shape"] == original["shape"]
        assert saved["Version"] == original["Version"]
        assert saved["FigureList"] == ["s", [["s", [[[1, 1], "1cRT"]]]]]

    def test_put_dance_tree_returns_400_for_invalid_tree_structure(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        write_json(dances_dir / "Existing Dance.json", make_dance_payload())

        response = client.put(
            f"/api/dances/{quote('Existing Dance.json', safe='')}/tree",
            json={"tree": {"id": "root", "text": "Broken"}},
        )

        assert response.status_code == 400
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "validation_error"
        assert body["field"] == "tree.type"

    def test_put_dance_tree_returns_400_for_conversion_error(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        write_json(dances_dir / "Existing Dance.json", make_dance_payload())
        payload = make_tree_payload("1cRT")
        del payload["tree"]["children"][0]["children"][0]["data"]["figureName"]

        response = client.put(
            f"/api/dances/{quote('Existing Dance.json', safe='')}/tree",
            json=payload,
        )

        assert response.status_code == 400
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "conversion_error"
        assert body["node_id"] == "figure-1"

    def test_put_dance_tree_returns_404_for_missing_dance(self, client_and_dances_dir):
        client, _ = client_and_dances_dir

        response = client.put(
            f"/api/dances/{quote('Missing Dance.json', safe='')}/tree",
            json=make_tree_payload(),
        )

        assert response.status_code == 404
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "not_found"

    def test_put_dance_tree_returns_400_for_malformed_json_body(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        write_json(dances_dir / "Existing Dance.json", make_dance_payload())

        response = client.put(
            f"/api/dances/{quote('Existing Dance.json', safe='')}/tree",
            data='{"tree": ',
            content_type="application/json",
        )

        assert response.status_code == 400
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "validation_error"
        assert body["field"] == "body"

    def test_put_dance_tree_allows_empty_group(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        dance_path = dances_dir / "Existing Dance.json"
        write_json(dance_path, make_dance_payload())
        payload = {
            "tree": {
                "id": "root",
                "text": "Existing Dance",
                "type": "root",
                "data": {},
                "children": [
                    {
                        "id": "group-1",
                        "text": "Parallel",
                        "type": "group",
                        "data": {"groupType": "p"},
                        "children": [],
                    }
                ],
            }
        }

        response = client.put(
            f"/api/dances/{quote('Existing Dance.json', safe='')}/tree",
            json=payload,
        )

        assert response.status_code == 200
        assert read_json(dance_path)["FigureList"] == ["s", [["p", []]]]


class TestDeleteDanceEndpoint:
    def test_delete_dance_moves_file_into_deleted_folder(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        dance_path = dances_dir / "Delete Me.json"
        write_json(dance_path, make_dance_payload("Delete Me"))

        response = client.delete(f"/api/dances/{quote('Delete Me.json', safe='')}")

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "ok"
        assert body["message"] == "Dance deleted"
        assert not dance_path.exists()
        deleted_dir = dances_dir / ".deleted"
        assert (deleted_dir / "Delete Me.json").exists()

    def test_delete_dance_creates_backup_before_moving(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        dance_path = dances_dir / "Delete Me.json"
        write_json(dance_path, make_dance_payload("Delete Me"))

        response = client.delete(f"/api/dances/{quote('Delete Me.json', safe='')}")

        assert response.status_code == 200
        assert list(dances_dir.glob("Delete Me.json.*.bak"))

    def test_delete_dance_returns_404_for_missing_file(self, client_and_dances_dir):
        client, _ = client_and_dances_dir

        response = client.delete(f"/api/dances/{quote('Missing Dance.json', safe='')}")

        assert response.status_code == 404
        body = response.get_json()
        assert body["status"] == "error"
        assert body["error"] == "not_found"

    def test_delete_dance_handles_deleted_name_collisions(self, client_and_dances_dir):
        client, dances_dir = client_and_dances_dir
        deleted_dir = dances_dir / ".deleted"
        deleted_dir.mkdir()
        write_json(deleted_dir / "Delete Me.json", make_dance_payload("Older Deleted"))
        dance_path = dances_dir / "Delete Me.json"
        write_json(dance_path, make_dance_payload("Delete Me"))

        response = client.delete(f"/api/dances/{quote('Delete Me.json', safe='')}")

        assert response.status_code == 200
        deleted_files = list(deleted_dir.glob("Delete Me*.json"))
        assert len(deleted_files) == 2
        assert any(path.name != "Delete Me.json" for path in deleted_files)
