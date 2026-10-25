from urllib.parse import quote

import GUI_DanceCreator_App as app_module


def _client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_dances_endpoint_returns_canonical_list():
    response = _client().get("/api/dances")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"dances"}
    assert isinstance(body["dances"], list)
    for item in body["dances"]:
        assert set(item) == {"id", "name", "revision", "incomplete"}


def test_dance_detail_returns_canonical_document_and_matching_revision():
    client = _client()
    dances = client.get("/api/dances").get_json()["dances"]
    if not dances:
        return
    item = dances[0]
    response = client.get(f"/api/dances/{quote(item['id'])}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["document"]["revision"] == body["revision"] == item["revision"]
    assert body["etag"] == f'"{body["revision"]}"'
    assert response.headers["ETag"] == body["etag"]
    assert isinstance(body["tree"], dict)
    assert isinstance(body["trace"], list)


def test_missing_dance_is_a_structured_not_found():
    response = _client().get("/api/dances/no-such-dance")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
