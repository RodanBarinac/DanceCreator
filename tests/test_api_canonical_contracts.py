import json
import base64
from copy import deepcopy
import io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZipFile

import pytest
from flask import Flask

import GUI_DanceCreator_App as app_module
from src.api.canonical import create_canonical_blueprint
from src.engine.domain.dance_model import DanceDocument
from src.engine.figures.capabilities import FigureRepository
from src.engine.persistence.archive import (
    export_archive,
    export_archive_bytes,
    validate_archive,
)


CANONICAL = {
    "formatVersion": 1,
    "metadata": {"name": "Contract Dance", "shape": "1/1"},
    "status": "complete",
    "unresolvedReferences": [],
    "revision": 0,
    "root": {
        "type": "group",
        "id": "root",
        "kind": "series",
        "children": [
            {
                "type": "figure",
                "id": "figure-1",
                "figureRef": "Step",
                "anchor": [1, 0],
                "addons": [],
            }
        ],
    },
}


@pytest.fixture
def canonical_client(tmp_path, monkeypatch):
    figures = tmp_path / "data" / "Figures"
    dances = tmp_path / "data" / "Dances"
    figures.mkdir(parents=True)
    dances.mkdir()
    (figures / "Step.json").write_text(
        json.dumps(
            {
                "Version": 2,
                "Name": "Step",
                "Desc": "A contract fixture",
                "Bars": 1,
                "Formation": "1x1",
                "Addons": {"Turn": {"Desc": "turn"}},
            }
        ),
        encoding="utf-8",
    )
    dance_path = dances / "Contract Dance.json"
    dance_path.write_text(json.dumps(CANONICAL, indent=2), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figures))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dances))
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client, dance_path


def test_capabilities_and_canonical_projection(canonical_client):
    client, _ = canonical_client

    figures = client.get("/api/figures")
    assert figures.status_code == 200
    assert figures.get_json()["figures"][0]["figureRef"] == "Step"
    assert figures.get_json()["figures"][0]["capabilities"]["validAddons"][0]["name"] == "Turn"

    response = client.get("/api/dances/Contract%20Dance")
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["document"]["root"]["children"][0]["id"] == "figure-1"
    assert body["tree"]["children"][0]["id"] == "figure-1"
    assert body["tree"]["children"][0]["figureRef"] == "Step"
    assert "trace" in body
    assert body["etag"] == '"0"'
    assert response.headers["ETag"] == '"0"'
    assert "validation" in body


def test_figure_preview_uses_active_dancers_anchor_and_addon_parameters(canonical_client):
    client, dance_path = canonical_client
    figure_path = dance_path.parent.parent / "Figures" / "Step.json"
    definition = json.loads(figure_path.read_text(encoding="utf-8"))
    definition["StartPos"] = [[0, -1], [0, 1], [1, -1], [1, 1]]
    definition["EndPos"] = [[0, -1], [0, 1], [1, 1], [1, -1]]
    definition["EndFacing"] = [[], [], [], []]
    definition["Addons"]["Shift"] = {
        "Version": 1,
        "StartPos": [[0, 0], [], [], []],
        "EndPos": [[0, 0], [], [], []],
        "EndFacing": [[0, -1], [], [], []],
    }
    figure_path.write_text(json.dumps(definition), encoding="utf-8")
    (figure_path.parent / "Solo.json").write_text(
        json.dumps({
            "Version": 2,
            "Name": "Solo",
            "Desc": "One active dancer",
            "Bars": 1,
            "StartPos": [[0, -1]],
            "EndPos": [[0, 0]],
            "Addons": {},
        }),
        encoding="utf-8",
    )

    response = client.post(
        "/api/figures/Step/preview",
        json={"anchor": [3, 3], "addons": []},
    )

    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["couples"] == 2
    assert len(body["incomingFloor"]) == 4
    assert len(body["outgoingFloor"]) == 4
    assert {
        tuple(item["position"])
        for item in body["incomingFloor"].values()
    } == {(3, 2), (3, 4), (4, 2), (4, 4)}
    assert {
        tuple(item["position"])
        for item in body["outgoingFloor"].values()
    } == {(3, 2), (3, 4), (4, 2), (4, 4)}
    incoming_by_name = {
        item["dancer"]["name"]: item for item in body["incomingFloor"].values()
    }
    outgoing_by_name = {
        item["dancer"]["name"]: item for item in body["outgoingFloor"].values()
    }
    assert incoming_by_name["1m"]["position"] == [3, 2]
    assert incoming_by_name["1m"]["facing"] == [3, -2]
    assert outgoing_by_name["1m"]["position"] == [3, 2]
    assert outgoing_by_name["1m"]["facing"] == [3, -2]

    solo_response = client.post(
        "/api/figures/Solo/preview",
        json={"addons": []},
    )
    assert solo_response.status_code == 200, solo_response.get_json()
    solo = solo_response.get_json()
    assert solo["couples"] == 1
    assert len(solo["incomingFloor"]) == len(solo["outgoingFloor"]) == 1
    solo_incoming = next(iter(solo["incomingFloor"].values()))
    solo_outgoing = next(iter(solo["outgoingFloor"].values()))
    assert solo_incoming["position"] == [1, -1]
    assert solo_incoming["facing"] == [1, 1]
    assert solo_outgoing["position"] == [1, 0]

    changed = client.post(
        "/api/figures/Step/preview",
        json={"anchor": [3, 3], "addons": ["Shift"]},
    )
    assert changed.status_code == 200, changed.get_json()
    preview = changed.get_json()
    incoming_by_name = {
        item["dancer"]["name"]: item for item in preview["incomingFloor"].values()
    }
    outgoing_by_name = {
        item["dancer"]["name"]: item for item in preview["outgoingFloor"].values()
    }
    assert incoming_by_name["1m"]["position"] == [3, 3]
    assert incoming_by_name["1m"]["facing"] == [3, -3]
    assert outgoing_by_name["1m"]["position"] == [3, 3]
    assert outgoing_by_name["1m"]["facing"] == [3, 2]



def test_generic_duration_addon_is_accepted_by_api_preview(canonical_client):
    client, dance_path = canonical_client
    figure_path = dance_path.parent.parent / "Figures" / "Step.json"
    definition = json.loads(figure_path.read_text(encoding="utf-8"))
    definition["StartPos"] = [[0, -1], [0, 1]]
    definition["EndPos"] = [[0, -1], [0, 1]]
    figure_path.write_text(json.dumps(definition), encoding="utf-8")

    response = client.post(
        "/api/figures/Step/preview",
        json={"addons": ["B3"]},
    )

    assert response.status_code == 200, response.get_json()
    assert set(response.get_json()["incomingFloor"]) == {"1m", "1w"}

def test_proposal_apply_revision_and_stale_rollback(canonical_client):
    client, dance_path = canonical_client
    proposal = client.post(
        "/api/dances/Contract%20Dance/proposals",
        json={
            "baseRevision": 0,
            "command": {
                "type": "updateAnchor",
                "nodeId": "figure-1",
                "anchor": [2, 1],
            },
        },
    )
    assert proposal.status_code == 200
    assert proposal.get_json()["proposal"]["document"]["root"]["children"][0]["anchor"] == [2, 1]
    proposal_id = proposal.get_json()["proposal"]["proposalId"]
    assert json.loads(dance_path.read_text(encoding="utf-8"))["revision"] == 0

    applied = client.post(
        "/api/dances/Contract%20Dance/apply",
        json={"baseRevision": 0, "proposalId": proposal_id},
    )
    assert applied.status_code == 200
    assert applied.get_json()["revision"] == 1
    assert applied.get_json()["etag"] == '"1"'
    assert json.loads(dance_path.read_text(encoding="utf-8"))["revision"] == 0

    stale = client.post(
        "/api/dances/Contract%20Dance/apply",
        json={"baseRevision": 0, "proposalId": proposal_id},
    )
    assert stale.status_code == 409
    assert stale.get_json()["error"]["code"] == "revision_conflict"
    assert json.loads(dance_path.read_text(encoding="utf-8"))["revision"] == 0


def test_apply_rejects_fabricated_candidate_documents(canonical_client):
    client, dance_path = canonical_client
    fabricated = dict(CANONICAL)
    fabricated["root"] = {
        "type": "group", "id": "root", "kind": "series", "children": []
    }
    response = client.post(
        "/api/dances/Contract%20Dance/apply",
        json={
            "baseRevision": 0,
            "proposal": {"baseRevision": 0, "document": fabricated},
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "malformed_request"
    assert json.loads(dance_path.read_text(encoding="utf-8"))["revision"] == 0


def test_composite_occurrence_projection_includes_embedded_root(canonical_client):
    client, dance_path = canonical_client
    composite = deepcopy(CANONICAL)
    composite["root"]["children"] = [{
        "type": "compositeOccurrence",
        "id": "composite-1",
        "figureRef": "Composite",
        "anchor": [1, 0],
        "addons": [],
        "root": {
            "type": "group", "id": "embedded-root", "kind": "series",
            "children": [{
                "type": "figure", "id": "nested-figure", "figureRef": "Step",
                "anchor": [1, 0], "addons": [],
            }],
        },
    }]
    dance_path.write_text(json.dumps(composite), encoding="utf-8")
    response = client.get("/api/dances/Contract%20Dance")
    tree = response.get_json()["tree"]
    occurrence = tree["children"][0]
    assert occurrence["type"] == "compositeOccurrence"
    assert occurrence["root"]["id"] == "embedded-root"
    assert occurrence["root"]["children"][0]["id"] == "nested-figure"


def test_apply_undo_redo_preserve_history_and_increment_revisions(canonical_client):
    client, _ = canonical_client
    proposed = client.post(
        "/api/dances/Contract%20Dance/proposals",
        json={"baseRevision": 0, "command": {
            "type": "updateAnchor", "nodeId": "figure-1", "anchor": [2, 1],
        }},
    ).get_json()["proposal"]
    applied = client.post("/api/dances/Contract%20Dance/apply", json={
        "baseRevision": 0, "proposalId": proposed["proposalId"],
    })
    assert applied.status_code == 200
    assert applied.get_json()["revision"] == 1

    persisted = client.post("/api/dances/Contract%20Dance/save", json={
        "baseRevision": 1, "document": applied.get_json()["document"],
    })
    assert persisted.status_code == 200
    assert persisted.get_json()["revision"] == 2

    undone = client.post("/api/dances/Contract%20Dance/undo", json={"baseRevision": 2})
    assert undone.status_code == 200
    assert undone.get_json()["revision"] == 3
    assert undone.get_json()["document"]["root"]["children"][0]["anchor"] == [1, 0]

    redone = client.post("/api/dances/Contract%20Dance/redo", json={"baseRevision": 3})
    assert redone.status_code == 200
    assert redone.get_json()["revision"] == 4
    assert redone.get_json()["document"]["root"]["children"][0]["anchor"] == [2, 1]


def test_same_base_concurrent_apply_commits_at_most_once(canonical_client):
    _, _ = canonical_client
    with app_module.app.test_client() as client:
        proposal = client.post(
            "/api/dances/Contract%20Dance/proposals",
            json={"baseRevision": 0, "command": {
                "type": "updateAnchor", "nodeId": "figure-1", "anchor": [2, 1],
            }},
        ).get_json()["proposal"]

    def apply_once():
        with app_module.app.test_client() as client:
            return client.post("/api/dances/Contract%20Dance/apply", json={
                "baseRevision": 0, "proposalId": proposal["proposalId"],
            }).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: apply_once(), range(2)))
    assert sorted(statuses) == [200, 409]


def test_malformed_and_jstree_writes_are_structured_errors(canonical_client):
    client, _ = canonical_client
    malformed = client.post("/api/dances/Contract%20Dance/proposals", json={})
    assert malformed.status_code == 400
    assert malformed.get_json()["error"]["code"] == "malformed_request"

    legacy_write = client.put(
        "/api/dances/Contract%20Dance/tree",
        json={"tree": {"id": "root", "children": []}},
    )
    assert legacy_write.status_code == 405
    assert legacy_write.get_json()["error"]["code"] == "method_not_allowed"


def test_incomplete_save_requires_confirmation(canonical_client):
    client, _ = canonical_client
    incomplete = dict(CANONICAL)
    incomplete["status"] = "incomplete"
    incomplete["unresolvedReferences"] = ["Missing"]
    incomplete["root"] = {
        "type": "group",
        "id": "root",
        "kind": "series",
        "children": [
            {
                "type": "figure",
                "id": "missing-1",
                "figureRef": "Missing",
                "anchor": [1, 0],
                "addons": [],
            }
        ],
    }
    response = client.post(
        "/api/dances/Contract%20Dance/save",
        json={"baseRevision": 0, "document": incomplete},
    )
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "incomplete_confirmation_required"

    confirmed = client.post(
        "/api/dances/Contract%20Dance/save",
        json={
            "baseRevision": 0,
            "document": incomplete,
            "confirmIncomplete": True,
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["document"]["status"] == "incomplete"
    assert confirmed.get_json()["trace"] == []
    assert confirmed.get_json()["execution"]["status"] == "failed"


def test_incomplete_save_rejects_non_reference_validation_errors(canonical_client):
    client, _ = canonical_client
    malformed_anchor = dict(CANONICAL)
    malformed_anchor["status"] = "incomplete"
    malformed_anchor["unresolvedReferences"] = ["Missing"]
    malformed_anchor["root"] = {
        "type": "group", "id": "root", "kind": "series", "children": [
            {"type": "figure", "id": "bad", "figureRef": "Missing",
             "anchor": [0, 1], "addons": []},
            {"type": "figure", "id": "unsupported", "figureRef": "Step",
             "anchor": [1, 0], "addons": ["Bogus"]},
        ],
    }
    result = client.post("/api/dances/Contract%20Dance/save", json={
        "baseRevision": 0, "document": malformed_anchor, "confirmIncomplete": True,
    })
    assert result.status_code == 400
    assert result.get_json()["error"]["code"] == "validation_error"


def test_stale_revision_is_rejected_for_save_undo_and_redo(canonical_client):
    client, _ = canonical_client
    assert client.post("/api/dances/Contract%20Dance/save", json={
        "baseRevision": 0, "document": CANONICAL,
    }).status_code == 200
    stale_save = client.post("/api/dances/Contract%20Dance/save", json={
        "baseRevision": 0, "document": CANONICAL,
    })
    stale_undo = client.post("/api/dances/Contract%20Dance/undo", json={"baseRevision": 0})
    stale_redo = client.post("/api/dances/Contract%20Dance/redo", json={"baseRevision": 0})
    assert [stale_save.status_code, stale_undo.status_code, stale_redo.status_code] == [409, 409, 409]
    assert all(r.get_json()["error"]["code"] == "revision_conflict"
               for r in (stale_save, stale_undo, stale_redo))


def test_archive_export_and_missing_dance(canonical_client, tmp_path):
    client, _ = canonical_client
    missing = client.get("/api/dances/missing")
    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "not_found"
    missing_archive = client.get("/api/dances/00000000000000000000000000000000")
    assert missing_archive.status_code == 404
    assert missing_archive.get_json()["error"]["code"] == "not_found"

    exported = client.post(
        "/api/archives/export",
        json={"danceId": "Contract Dance"},
    )
    assert exported.status_code == 200
    assert exported.get_json()["package"]


def test_archive_import_uses_isolated_archive_store_and_preserves_assets(canonical_client, tmp_path):
    client, dance_path = canonical_client
    source = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    package_path = tmp_path / "source.zip"
    export_archive(source, repository, package_path, assets={"assets/note.txt": b"asset"})
    raw_zip = io.BytesIO(package_path.read_bytes())
    with ZipFile(raw_zip, "r") as archive:
        assert archive.read("assets/note.txt") == b"asset"
    package = base64.b64encode(raw_zip.getvalue()).decode("ascii")
    legacy_files_before = {p.name: p.read_bytes() for p in dance_path.parent.glob("*.json")}

    response = client.post("/api/archives/import", json={"package": package})
    assert response.status_code == 200
    imported = response.get_json()
    assert imported["danceId"]
    assert imported["repositoryScope"] == "archive"
    duplicate = client.post("/api/archives/import", json={"package": package})
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "name_collision"

    copied = client.post("/api/archives/import", json={
        "package": package, "name": "Contract Copy",
    })
    assert copied.status_code == 200
    assert copied.get_json()["document"]["metadata"]["name"] == "Contract Copy"

    scoped_export = client.post("/api/archives/export", json={
        "danceId": imported["danceId"],
    })
    assert scoped_export.status_code == 200
    exported_package = validate_archive(base64.b64decode(scoped_export.get_json()["package"]))
    assert exported_package.assets["assets/note.txt"] == b"asset"

    replaced = client.post("/api/archives/import", json={
        "package": package,
        "replace": True,
        "confirmReplace": True,
        "expectedRevision": 0,
    })
    assert replaced.status_code == 200
    assert replaced.get_json()["document"]["revision"] == 1
    stale_replace = client.post("/api/archives/import", json={
        "package": package,
        "replace": True,
        "confirmReplace": True,
        "expectedRevision": 0,
    })
    assert stale_replace.status_code == 409
    assert stale_replace.get_json()["error"]["code"] == "revision_conflict"
    assert client.get(f"/api/dances/{imported['danceId']}").get_json()["revision"] == 1

    stored = next((dance_path.parent / ".archive-store" / "dances").glob("*/assets/note.txt"))
    assert stored.read_bytes() == b"asset"
    assert {p.name: p.read_bytes() for p in dance_path.parent.glob("*.json")} == legacy_files_before


@pytest.mark.parametrize("flags", [
    {"replace": "false", "confirmReplace": "false"},
    {"replace": True, "confirmReplace": "false"},
])
def test_archive_import_requires_boolean_replacement_flags(canonical_client, tmp_path, flags):
    client, dance_path = canonical_client
    document = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    source = tmp_path / "flag-check.dancepkg"
    export_archive(document, repository, source)
    response = client.post("/api/archives/import", json={
        "package": base64.b64encode(source.read_bytes()).decode("ascii"),
        "expectedRevision": 0,
        **flags,
    })

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"
    assert not (dance_path.parent / ".archive-store" / "dances").exists()


def test_archive_replace_of_missing_target_is_not_treated_as_an_import(
    canonical_client, tmp_path,
):
    client, dance_path = canonical_client
    document = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    source = tmp_path / "missing-target.dancepkg"
    export_archive(document, repository, source)
    response = client.post("/api/archives/import", json={
        "package": base64.b64encode(source.read_bytes()).decode("ascii"),
        "replace": True,
        "confirmReplace": True,
        "expectedRevision": 0,
    })

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "replacement_target_not_found"
    assert not (dance_path.parent / ".archive-store" / "dances").exists()


def test_archive_replace_uses_current_api_revision_and_invalidates_unsaved_history(
    canonical_client, tmp_path,
):
    client, dance_path = canonical_client
    document = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    source = tmp_path / "replace-current.dancepkg"
    export_archive(document, repository, source)
    package = base64.b64encode(source.read_bytes()).decode("ascii")
    imported = client.post("/api/archives/import", json={"package": package}).get_json()
    dance_id = imported["danceId"]
    client.get(f"/api/dances/{dance_id}")
    proposal = client.post(f"/api/dances/{dance_id}/proposals", json={
        "baseRevision": 0,
        "command": {
            "type": "updateAnchor",
            "nodeId": "figure-1",
            "anchor": [2, 1],
        },
    }).get_json()["proposal"]
    applied = client.post(f"/api/dances/{dance_id}/apply", json={
        "baseRevision": 0,
        "proposalId": proposal["proposalId"],
    })
    assert applied.status_code == 200
    assert applied.get_json()["revision"] == 1

    replaced = client.post("/api/archives/import", json={
        "package": package,
        "replace": True,
        "confirmReplace": True,
        "expectedRevision": 1,
    })

    assert replaced.status_code == 200, replaced.get_json()
    assert replaced.get_json()["document"]["revision"] == 2
    current = client.get(f"/api/dances/{dance_id}").get_json()
    assert current["revision"] == 2
    assert current["document"]["root"]["children"][0]["anchor"] == [1, 0]


def test_archive_scoped_save_can_rename_without_changing_store_identity(
    canonical_client, tmp_path,
):
    client, dance_path = canonical_client
    document = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    source = tmp_path / "rename-package.dancepkg"
    export_archive(document, repository, source)
    imported = client.post("/api/archives/import", json={
        "package": base64.b64encode(source.read_bytes()).decode("ascii"),
    }).get_json()
    dance_id = imported["danceId"]
    renamed = deepcopy(imported["document"])
    renamed["metadata"]["name"] = "Renamed Dance"

    saved = client.post(f"/api/dances/{dance_id}/save", json={
        "baseRevision": 0,
        "document": renamed,
    })

    assert saved.status_code == 200, saved.get_json()
    assert saved.get_json()["revision"] == 1
    listed = client.get("/api/dances").get_json()["dances"]
    assert any(item["id"] == dance_id and item["name"] == "Renamed Dance" for item in listed)
    assert client.get(f"/api/dances/{dance_id}").get_json()["document"]["metadata"]["name"] == "Renamed Dance"


def test_archive_api_workers_refresh_cached_revision_after_another_worker_saves(
    canonical_client,
):
    first_client, dance_path = canonical_client
    document = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    source = export_archive_bytes(document, repository)
    imported = first_client.post("/api/archives/import", json={
        "package": base64.b64encode(source).decode("ascii"),
    }).get_json()
    dance_id = imported["danceId"]

    second_app = Flask("second-api-worker")
    second_app.config["TESTING"] = True
    second_app.register_blueprint(create_canonical_blueprint(app_module))
    second_client = second_app.test_client()
    assert second_client.get(f"/api/dances/{dance_id}").get_json()["revision"] == 0
    second_proposal = second_client.post(f"/api/dances/{dance_id}/proposals", json={
        "baseRevision": 0,
        "command": {
            "type": "updateAnchor",
            "nodeId": "figure-1",
            "anchor": [2, 1],
        },
    }).get_json()["proposal"]
    second_apply = second_client.post(f"/api/dances/{dance_id}/apply", json={
        "baseRevision": 0,
        "proposalId": second_proposal["proposalId"],
    })
    assert second_apply.status_code == 200
    replacement = first_client.post("/api/archives/import", json={
        "package": base64.b64encode(source).decode("ascii"),
        "replace": True,
        "confirmReplace": True,
        "expectedRevision": 0,
    })
    assert replacement.status_code == 200
    stale = second_client.post(f"/api/dances/{dance_id}/save", json={
        "baseRevision": second_apply.get_json()["revision"],
        "document": second_apply.get_json()["document"],
    })

    assert stale.status_code == 409
    assert stale.get_json()["error"]["code"] == "revision_conflict"
    assert first_client.get(f"/api/dances/{dance_id}").get_json()["revision"] == 1


def test_archive_rename_collision_preserves_both_stored_dances(canonical_client, tmp_path):
    client, dance_path = canonical_client
    document = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    source = tmp_path / "collision-package.dancepkg"
    export_archive(document, repository, source)
    package = base64.b64encode(source.read_bytes()).decode("ascii")
    first = client.post("/api/archives/import", json={"package": package}).get_json()
    second = client.post("/api/archives/import", json={
        "package": package,
        "name": "Other Dance",
    }).get_json()
    candidate = deepcopy(first["document"])
    candidate["metadata"]["name"] = "Other Dance"

    response = client.post(f"/api/dances/{first['danceId']}/save", json={
        "baseRevision": 0,
        "document": candidate,
    })

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "name_collision"
    assert client.get(f"/api/dances/{first['danceId']}").get_json()["document"]["metadata"]["name"] == "Contract Dance"
    assert client.get(f"/api/dances/{second['danceId']}").get_json()["document"]["metadata"]["name"] == "Other Dance"


def test_archive_export_uses_current_api_document_and_keeps_scoped_assets(
    canonical_client, tmp_path,
):
    client, dance_path = canonical_client
    document = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    source = tmp_path / "current-export.dancepkg"
    export_archive(document, repository, source, assets={"assets/note.txt": b"asset"})
    imported = client.post("/api/archives/import", json={
        "package": base64.b64encode(source.read_bytes()).decode("ascii"),
    }).get_json()
    dance_id = imported["danceId"]
    proposal = client.post(f"/api/dances/{dance_id}/proposals", json={
        "baseRevision": 0,
        "command": {
            "type": "updateAnchor",
            "nodeId": "figure-1",
            "anchor": [2, 1],
        },
    }).get_json()["proposal"]
    applied = client.post(f"/api/dances/{dance_id}/apply", json={
        "baseRevision": 0,
        "proposalId": proposal["proposalId"],
    })
    assert applied.status_code == 200

    exported = client.post("/api/archives/export", json={"danceId": dance_id})

    assert exported.status_code == 200
    package = validate_archive(base64.b64decode(exported.get_json()["package"]))
    assert package.document.revision == 1
    assert package.document.root.children[0].anchor == (2, 1)
    assert package.assets["assets/note.txt"] == b"asset"


def test_imported_archive_is_listed_and_readable_by_its_store_id(canonical_client, tmp_path):
    client, dance_path = canonical_client
    document = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    source = tmp_path / "readable.dancepkg"
    export_archive(document, repository, source)
    imported = client.post("/api/archives/import", json={
        "package": base64.b64encode(source.read_bytes()).decode("ascii"),
    })
    assert imported.status_code == 200
    dance_id = imported.get_json()["danceId"]

    listed = client.get("/api/dances").get_json()["dances"]
    assert any(item["id"] == dance_id for item in listed)
    detail = client.get(f"/api/dances/{dance_id}")
    assert detail.status_code == 200
    assert detail.get_json()["document"]["metadata"]["name"] == "Contract Dance"
    assert detail.get_json()["document"]["root"]["children"][0]["figureRef"] == "Step"


def test_position_key_mapping_matches_legacy_floor_contract():
    assert app_module._dance_position_key((1, -1)) == "1m"
    assert app_module._dance_position_key((1, 1)) == "1w"
    assert app_module._dance_position_key((1, 10)) == "1:10"
    assert app_module._dance_position_key((1.5, 3.25)) == "1.5:3.25"
    assert app_module._dance_position_key((1.0, -1.0)) == "1m"


def test_floor_serialization_preserves_fractional_coordinates():
    class Dancer:
        name = "Dancer"
        gender = "person"

    class Floor:
        name = "fractional"
        maxRow = 2
        AktBar = 3
        DanceFloorMap = {(1.5, 1.25): (Dancer(), (2.5, -1.0))}

    result = app_module._serialize_floor(Floor())
    assert result["positions"]["1.5:1.25"]["coord"] == [1.5, 1.25]


def test_api_trace_serializes_engine_snapshots_and_last_valid_floor(canonical_client):
    client, dance_path = canonical_client
    figure_path = dance_path.parents[2] / "data" / "Figures" / "Step.json"
    definition = json.loads(figure_path.read_text(encoding="utf-8"))
    definition.update(
        StartPos=[[0, -1]],
        EndPos=[[0, 0]],
        CriptDesc=["step"],
    )
    figure_path.write_text(json.dumps(definition), encoding="utf-8")

    response = client.get("/api/dances/Contract%20Dance/trace")

    assert response.status_code == 200
    body = response.get_json()
    assert body["execution"]["status"] == "completed"
    assert body["trace"]
    assert body["trace"][0]["incomingFloor"]
    assert body["trace"][0]["outgoingFloor"]
    assert body["execution"]["lastValidFloor"]
    assert body["execution"]["lastValidFloor"]["1:0"]["dancer"]["name"] == "1m"


def test_failed_parallel_trace_keeps_last_valid_floor_and_conflict_details(
    canonical_client,
):
    client, dance_path = canonical_client
    figures = dance_path.parents[2] / "data" / "Figures"
    for name, start in (("ManStep", [0, -1]), ("LadyStep", [0, 1])):
        (figures / f"{name}.json").write_text(json.dumps({
            "Version": 2,
            "Name": name,
            "Bars": 1,
            "Formation": "1x1",
            "StartPos": [start],
            "EndPos": [[0, 0]],
            "CriptDesc": [name],
            "Addons": {},
        }), encoding="utf-8")
    conflict_document = deepcopy(CANONICAL)
    conflict_document["root"]["children"] = [{
        "type": "group",
        "id": "parallel",
        "kind": "parallel",
        "children": [
            {
                "type": "figure",
                "id": "man-step",
                "figureRef": "ManStep",
                "anchor": [1, 0],
                "addons": [],
            },
            {
                "type": "figure",
                "id": "lady-step",
                "figureRef": "LadyStep",
                "anchor": [1, 0],
                "addons": [],
            },
        ],
    }]
    dance_path.write_text(json.dumps(conflict_document), encoding="utf-8")

    response = client.get("/api/dances/Contract%20Dance/trace")

    assert response.status_code == 200
    body = response.get_json()
    assert body["execution"]["status"] == "failed"
    assert body["execution"]["lastValidFloor"]
    parallel_record = next(record for record in body["trace"] if record["nodeId"] == "parallel")
    assert parallel_record["outgoingFloor"] is None
    assert parallel_record["conflict"]["code"] == "parallel_write_conflict"
    assert body["validation"]["firstBlocking"]["code"] == "parallel_conflict"


def test_composite_figures_appear_in_catalog_without_invented_capabilities(
    canonical_client,
):
    client, dance_path = canonical_client
    figures = dance_path.parents[2] / "data" / "Figures"
    (figures / "Composite.json").write_text(json.dumps({
        "Version": 3,
        "Name": "Composite",
        "Desc": "A composite figure",
        "Formation": "1x1",
        "FigureList": ["s", [[[0, -1], "Step"]]],
    }), encoding="utf-8")

    listed = client.get("/api/figures").get_json()["figures"]
    composite = next(item for item in listed if item["figureRef"] == "Composite")
    detail = client.get("/api/figures/Composite")

    assert composite["version"] == 3
    assert composite["capabilities"] is None
    assert detail.status_code == 200
    assert detail.get_json()["version"] == 3
    assert detail.get_json()["capabilities"] is None


def test_imported_archive_can_be_edited_and_saved_with_scoped_assets(canonical_client, tmp_path):
    client, dance_path = canonical_client
    document = DanceDocument.from_json(deepcopy(CANONICAL))
    repository = FigureRepository(
        dance_path.parents[2] / "data" / "Figures",
        dance_path.parents[2] / "data" / "Dances",
    )
    source = tmp_path / "editable.dancepkg"
    export_archive(
        document,
        repository,
        source,
        assets={"assets/note.txt": b"keep me"},
    )
    imported = client.post("/api/archives/import", json={
        "package": base64.b64encode(source.read_bytes()).decode("ascii"),
    }).get_json()
    dance_id = imported["danceId"]

    proposed = client.post(f"/api/dances/{dance_id}/proposals", json={
        "baseRevision": 0,
        "command": {
            "type": "updateAnchor",
            "nodeId": "figure-1",
            "anchor": [2, 1],
        },
    })
    assert proposed.status_code == 200
    proposal = proposed.get_json()["proposal"]
    applied = client.post(f"/api/dances/{dance_id}/apply", json={
        "baseRevision": 0,
        "proposalId": proposal["proposalId"],
    })
    assert applied.status_code == 200
    saved = client.post(f"/api/dances/{dance_id}/save", json={
        "baseRevision": 1,
        "document": applied.get_json()["document"],
    })
    assert saved.status_code == 200
    assert saved.get_json()["revision"] == 2

    stored = client.post("/api/archives/export", json={"danceId": dance_id})
    assert stored.status_code == 200
    package = validate_archive(base64.b64decode(stored.get_json()["package"]))
    assert package.document.revision == 2
    assert package.document.root.children[0].anchor == (2, 1)
    assert package.assets["assets/note.txt"] == b"keep me"


def test_legacy_read_adapts_without_rewriting_source(tmp_path, monkeypatch):
    figures = tmp_path / "data" / "Figures"
    dances = tmp_path / "data" / "Dances"
    figures.mkdir(parents=True)
    dances.mkdir()
    (figures / "Step.json").write_text(
        json.dumps({"Version": 2, "Name": "Step", "Bars": 1, "Addons": {}}),
        encoding="utf-8",
    )
    source = dances / "Legacy.json"
    source.write_text(
        json.dumps(
            {
                "Version": 2,
                "Name": "Legacy",
                "FigureList": ["s", [[[1, 1], ["Step", []]]]],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    original = source.read_bytes()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app_module, "FIGURES_DIR", str(figures))
    monkeypatch.setattr(app_module, "DANCES_DIR", str(dances))
    with app_module.app.test_client() as client:
        response = client.get("/api/dances/Legacy")
    assert response.status_code == 200
    assert response.get_json()["document"]["root"]["children"][0]["id"]
    assert source.read_bytes() == original
