import json

import GUI_DanceCreator_App as app_module


def _client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_dance_tree_get_is_canonical_projection():
    client = _client()
    dances = client.get("/api/dances").get_json()["dances"]
    if not dances:
        return
    response = client.get(f"/api/dances/{dances[0]['id']}/tree")
    assert response.status_code == 200
    body = response.get_json()
    assert body["tree"] == body["document"]["root"] or body["tree"]["id"] == body["document"]["root"]["id"]
    assert "trace" in body and "revision" in body


def test_dance_tree_not_found_has_structured_error():
    response = _client().get("/api/dances/NonExistentDance12345/tree")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_tree_projection_preserves_stable_node_ids_and_nested_nodes():
    client = _client()
    dances = client.get("/api/dances").get_json()["dances"]
    if not dances:
        return
    body = client.get(f"/api/dances/{dances[0]['id']}").get_json()

    def check(node):
        assert node["id"]
        assert node["type"] in {"group", "figure", "compositeOccurrence"}
        if node["type"] == "group":
            assert isinstance(node["children"], list)
            for child in node["children"]:
                check(child)
        if node["type"] == "compositeOccurrence":
            check(node["root"])

    check(body["tree"])


def test_tree_put_is_rejected_without_mutating_legacy_data(tmp_path, monkeypatch):
    figures = tmp_path / "data" / "Figures"
    dances_dir = tmp_path / "data" / "Dances"
    figures.mkdir(parents=True)
    dances_dir.mkdir()
    (figures / "Step.json").write_text(json.dumps({
        "Version": 2, "Name": "Step", "Bars": 1, "Addons": {},
    }), encoding="utf-8")
    dance = {
        "formatVersion": 1,
        "metadata": {"name": "No tree writes"},
        "status": "complete",
        "unresolvedReferences": [],
        "revision": 0,
        "root": {"type": "group", "id": "root", "kind": "series", "children": []},
    }
    path = dances_dir / "No tree writes.json"
    path.write_text(json.dumps(dance), encoding="utf-8")
    before = path.read_bytes()
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figures))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dances_dir))

    response = _client().put(
        "/api/dances/No%20tree%20writes/tree",
        json={"tree": {"id": "root", "children": []}},
    )
    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "method_not_allowed"
    assert path.read_bytes() == before
