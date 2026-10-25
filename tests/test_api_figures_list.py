from urllib.parse import quote

import GUI_DanceCreator_App as app_module


def _client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_figures_endpoint_returns_capabilities():
    response = _client().get("/api/figures")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"figures"}
    assert isinstance(body["figures"], list)
    for figure in body["figures"]:
        assert {"figureRef", "name", "description", "version", "capabilities"} <= set(figure)
        if figure["version"] == 3:
            assert figure["capabilities"] is None
        else:
            assert {"bars", "formation", "validAddons", "supportsPreview", "capabilityVersion", "durationAddonPattern"} <= set(
                figure["capabilities"]
            )


def test_figure_detail_returns_authoritative_capabilities():
    client = _client()
    figures = client.get("/api/figures").get_json()["figures"]
    if not figures:
        return
    figure_ref = figures[0]["figureRef"]
    response = client.get(f"/api/figures/{quote(figure_ref)}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["figureRef"] == figure_ref
    if body["version"] == 3:
        assert body["capabilities"] is None
    else:
        assert isinstance(body["capabilities"]["validAddons"], list)
