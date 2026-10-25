import json

import GUI_DanceCreator_App as app_module


DOCUMENT = {
    "formatVersion": 1,
    "metadata": {"name": "Mutation Dance", "shape": "1/1"},
    "status": "complete",
    "unresolvedReferences": [],
    "revision": 0,
    "root": {
        "type": "group",
        "id": "root",
        "kind": "series",
        "children": [{
            "type": "figure",
            "id": "step-1",
            "figureRef": "Step",
            "anchor": [1, 1],
            "addons": [],
        }],
    },
}


def _fixture(tmp_path, monkeypatch):
    figures = tmp_path / "data" / "Figures"
    dances = tmp_path / "data" / "Dances"
    figures.mkdir(parents=True)
    dances.mkdir()
    (figures / "Step.json").write_text(json.dumps({
        "Version": 2, "Name": "Step", "Bars": 1, "Addons": {},
    }), encoding="utf-8")
    path = dances / "Mutation Dance.json"
    path.write_text(json.dumps(DOCUMENT), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figures))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dances))
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client(), path


def _proposal(client):
    response = client.post("/api/dances/Mutation%20Dance/proposals", json={
        "baseRevision": 0,
        "command": {"type": "updateAnchor", "nodeId": "step-1", "anchor": [2, 1]},
    })
    assert response.status_code == 200, response.get_json()
    return response.get_json()["proposal"]


def test_semantic_apply_persists_and_retains_undo_history(tmp_path, monkeypatch):
    client, path = _fixture(tmp_path, monkeypatch)
    proposal = _proposal(client)
    response = client.post("/api/dances/Mutation%20Dance/apply", json={
        "baseRevision": 0, "proposalId": proposal["proposalId"],
    })
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["revision"] == 1
    assert json.loads(path.read_text(encoding="utf-8"))["revision"] == 0

    undo = client.post("/api/dances/Mutation%20Dance/undo", json={"baseRevision": 1})
    assert undo.status_code == 200
    assert undo.get_json()["document"]["root"]["children"][0]["anchor"] == [1, 1]


def test_save_uses_expected_revision_or_etag_and_stale_save_rolls_back(tmp_path, monkeypatch):
    client, path = _fixture(tmp_path, monkeypatch)
    saved = client.post("/api/dances/Mutation%20Dance/save", json={
        "baseRevision": 0, "document": DOCUMENT,
    })
    assert saved.status_code == 200, saved.get_json()
    assert saved.get_json()["revision"] == 1

    stale = client.post("/api/dances/Mutation%20Dance/save", json={
        "baseRevision": 0, "document": DOCUMENT,
    })
    assert stale.status_code == 409
    assert stale.get_json()["error"]["code"] == "revision_conflict"
    assert json.loads(path.read_text(encoding="utf-8"))["revision"] == 1

    etag_save = client.post(
        "/api/dances/Mutation%20Dance/save",
        json={"document": saved.get_json()["document"]},
        headers={"If-Match": '"1"'},
    )
    assert etag_save.status_code == 200
    assert etag_save.get_json()["revision"] == 2


def test_tree_write_and_legacy_full_document_put_are_not_mutations(tmp_path, monkeypatch):
    client, path = _fixture(tmp_path, monkeypatch)
    before = path.read_bytes()
    tree_write = client.put(
        "/api/dances/Mutation%20Dance/tree",
        json={"tree": {"id": "root", "children": []}},
    )
    legacy_put = client.put("/api/dances/Mutation%20Dance", json=DOCUMENT)
    assert tree_write.status_code == 405
    assert tree_write.get_json()["error"]["code"] == "method_not_allowed"
    assert legacy_put.status_code == 405
    assert path.read_bytes() == before
