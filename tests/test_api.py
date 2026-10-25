from urllib.parse import quote

from GUI_DanceCreator_App import app


def _client():
    return app.test_client()


def test_api_figures_list_uses_canonical_capabilities():
    response = _client().get("/api/figures")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"figures"}
    if body["figures"]:
        figure = body["figures"][0]
        assert {"figureRef", "name", "version", "capabilities"} <= set(figure)
        assert "validAddons" in figure["capabilities"]


def test_api_figure_detail_returns_capabilities():
    figures = _client().get("/api/figures").get_json()["figures"]
    if not figures:
        return
    response = _client().get(f"/api/figures/{quote(figures[0]['figureRef'])}")
    assert response.status_code == 200
    assert response.get_json()["figureRef"] == figures[0]["figureRef"]
    assert "capabilities" in response.get_json()


def test_api_dances_list_uses_canonical_identifiers_and_revisions():
    response = _client().get("/api/dances")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"dances"}
    for dance in body["dances"]:
        assert {"id", "name", "revision", "incomplete"} <= set(dance)


def test_api_dance_detail_returns_document_projection_and_trace():
    dances = _client().get("/api/dances").get_json()["dances"]
    if not dances:
        return
    response = _client().get(f"/api/dances/{quote(dances[0]['id'])}")
    assert response.status_code == 200
    body = response.get_json()
    assert {"document", "tree", "trace", "revision", "etag", "execution"} <= set(body)
    assert body["tree"]["id"] == body["document"]["root"]["id"]
    assert response.headers["ETag"] == body["etag"]


def test_legacy_jstree_listing_is_not_a_canonical_contract():
    assert _client().get("/api/tree").status_code == 404


def test_dancefloor_init_remains_available():
    response = _client().post("/api/dancefloor/init", json={"couples": 2, "name": "test"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "test"
    assert body["couples"] == 2
    assert body["tick"] == 1
    assert body["positions"]["1m"]["coord"] == [1, -1]
    assert body["positions"]["1m"]["facing"] == [1, 1]
    assert body["positions"]["1w"]["coord"] == [1, 1]
    assert body["positions"]["1w"]["facing"] == [1, -1]
    assert body["positions"]["2m"]["coord"] == [2, -1]
    assert body["positions"]["2w"]["coord"] == [2, 1]


def test_dancefloor_execute_remains_available():
    response = _client().post(
        "/api/dancefloor/execute",
        json={"figure": "1cCast1p", "couples": 3, "anchor": [1, 0]},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert "floor" in body and "crips" in body
