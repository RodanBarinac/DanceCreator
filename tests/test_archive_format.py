import json
import zipfile
import pytest
import src.engine.persistence.archive as archive_module

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    FigureOccurrence,
    GroupNode,
)
from src.engine.figures.capabilities import FigureRepository
from src.engine.persistence.archive import (
    ArchiveError,
    export_archive,
    validate_archive,
)


def _atomic(name="Atomic", addons=None):
    return {
        "Name": name,
        "Desc": "atomic definition",
        "Version": 2,
        "Bars": 1,
        "Formation": "reel",
        "Addons": addons or {},
    }


def _composite(name="Composite"):
    return {
        "Name": name,
        "Desc": "composite definition",
        "Version": 3,
        "FigureList": ["s", [[[0, 0], ["Atomic", ["Hands"]]]]],
    }


def _repository(tmp_path):
    figures = tmp_path / "figures"
    dances = tmp_path / "dances"
    figures.mkdir()
    dances.mkdir()
    (figures / "Atomic.json").write_text(
        json.dumps(_atomic(addons={"Hands": {}})), encoding="utf-8"
    )
    (figures / "Composite.json").write_text(
        json.dumps(_composite()), encoding="utf-8"
    )
    return FigureRepository(figures, dances)


def _document():
    return DanceDocument(
        1,
        {"name": "Archive test", "custom": {"owner": "dancer"}},
        GroupNode(
            "root",
            "series",
            (
                FigureOccurrence("atomic-a", "Atomic", (1, 2), ("Hands",)),
                GroupNode(
                    "parallel",
                    "parallel",
                    (
                        FigureOccurrence("atomic-b", "Atomic", (3, 4), ()),
                        CompositeOccurrence(
                            "composite-occ",
                            "Composite",
                            (5, 6),
                            (),
                            GroupNode(
                                "embedded-root",
                                "series",
                                (FigureOccurrence("embedded-atomic", "Atomic", (7, 8), ("Hands",)),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        revision=17,
    )


def _write_package(path, manifest, dance, members):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("package.json", json.dumps(manifest))
        archive.writestr("dance.json", json.dumps(dance))
        for name, content in members.items():
            archive.writestr(name, json.dumps(content))


def _manifest(*, figures=None, incomplete=False, format_version=1):
    return {
        "formatVersion": format_version,
        "packageId": "test-package",
        "danceName": "Archive test",
        "figures": figures or {
            "Atomic": "figures/Atomic.json",
            "Composite": "figures/Composite.json",
        },
        "incomplete": incomplete,
    }


def test_export_round_trips_tree_and_bundles_all_recursive_references(tmp_path):
    repository = _repository(tmp_path)
    document = _document()
    assets = {"assets/cover.txt": b"cover"}
    archive_path = export_archive(
        document, repository, tmp_path / "dance.dancepkg", assets=assets,
        package_id="stable-test-id",
    )

    package = validate_archive(archive_path)

    assert package.document == document
    assert set(package.figures) == {"Atomic", "Composite"}
    assert package.figures["Composite"]["Version"] == 3
    assert package.assets == assets
    assert package.executable is True
    with zipfile.ZipFile(archive_path) as archive:
        first = archive.read("dance.json")
        second = archive.read("package.json")
    second_path = export_archive(
        document, repository, tmp_path / "dance-again.dancepkg", assets=assets,
        package_id="stable-test-id",
    )
    with zipfile.ZipFile(second_path) as archive:
        assert archive.read("dance.json") == first
        assert archive.read("package.json") == second
    assert second_path.read_bytes() == archive_path.read_bytes()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda manifest, dance: manifest.update(formatVersion=2), "formatVersion"),
        (lambda manifest, dance: manifest["figures"].clear(), "reference"),
        (lambda manifest, dance: dance["root"].update(type="unknown"), "dance.json"),
        (lambda manifest, dance: manifest.update(incomplete=True), "incomplete"),
    ],
)
def test_rejects_wrong_version_mismatched_refs_malformed_tree_and_status(
    tmp_path, mutation, message
):
    path = tmp_path / "bad.dancepkg"
    manifest = _manifest()
    dance = _document().to_json()
    mutation(manifest, dance)
    _write_package(
        path,
        manifest,
        dance,
        {
            "figures/Atomic.json": _atomic(addons={"Hands": {}}),
            "figures/Composite.json": _composite(),
        },
    )

    with pytest.raises(ArchiveError, match=message):
        validate_archive(path)


def test_rejects_non_integer_archive_version_and_non_finite_occurrence_anchor(tmp_path):
    floating_version = tmp_path / "floating-version.dancepkg"
    manifest = _manifest(format_version=1.0)
    _write_package(
        floating_version,
        manifest,
        _document().to_json(),
        {
            "figures/Atomic.json": _atomic(addons={"Hands": {}}),
            "figures/Composite.json": _composite(),
        },
    )
    with pytest.raises(ArchiveError, match="formatVersion"):
        validate_archive(floating_version)

    non_finite = tmp_path / "non-finite.dancepkg"
    dance = _document().to_json()
    dance["root"]["children"][0]["anchor"][0] = float("inf")
    with zipfile.ZipFile(non_finite, "w") as archive:
        archive.writestr("package.json", json.dumps(_manifest()))
        archive.writestr("dance.json", json.dumps(dance))
        archive.writestr("figures/Atomic.json", json.dumps(_atomic(addons={"Hands": {}})))
        archive.writestr("figures/Composite.json", json.dumps(_composite()))
    with pytest.raises(ArchiveError, match="finite|JSON"):
        validate_archive(non_finite)


def test_rejects_missing_extra_members_and_duplicate_zip_names(tmp_path):
    missing = tmp_path / "missing.dancepkg"
    _write_package(
        missing, _manifest(), _document().to_json(), {}
    )
    with pytest.raises(ArchiveError, match="figures/Atomic.json"):
        validate_archive(missing)

    extra = tmp_path / "extra.dancepkg"
    _write_package(
        extra,
        _manifest(),
        _document().to_json(),
        {"figures/Atomic.json": _atomic(), "unexpected.json": {}},
    )
    with pytest.raises(ArchiveError, match="unexpected.json"):
        validate_archive(extra)

    duplicate = tmp_path / "duplicate.dancepkg"
    with zipfile.ZipFile(duplicate, "w") as archive:
        archive.writestr("package.json", json.dumps(_manifest()))
        archive.writestr("package.json", json.dumps(_manifest()))
    with pytest.raises(ArchiveError, match="duplicate"):
        validate_archive(duplicate)


def test_rejects_archive_members_with_file_directory_path_conflicts(tmp_path):
    path = tmp_path / "path-conflict.dancepkg"
    _write_package(
        path,
        _manifest(),
        _document().to_json(),
        {
            "figures/Atomic.json": _atomic(addons={"Hands": {}}),
            "figures/Composite.json": _composite(),
            "assets/x": {"name": "file"},
            "assets/x/y": {"name": "child"},
        },
    )

    with pytest.raises(ArchiveError, match="path conflict"):
        validate_archive(path)


def test_deeply_nested_json_is_reported_as_archive_error(tmp_path):
    path = tmp_path / "deep-json.dancepkg"
    nested = b"[" * 1500 + b"0" + b"]" * 1500
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "package.json",
            b'{"deep":' + nested + b"}",
        )
        archive.writestr("dance.json", "{}")

    with pytest.raises(ArchiveError, match="invalid JSON"):
        validate_archive(path)


def test_rejects_overflowing_json_number_before_accepting_package(tmp_path):
    path = tmp_path / "overflowing-number.dancepkg"
    dance = json.dumps(_document().to_json()).replace(
        '"owner": "dancer"',
        '"owner": "dancer", "weight": 1e999',
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("package.json", json.dumps(_manifest()))
        archive.writestr("dance.json", dance)
        archive.writestr(
            "figures/Atomic.json",
            json.dumps(_atomic(addons={"Hands": {}})),
        )
        archive.writestr("figures/Composite.json", json.dumps(_composite()))

    with pytest.raises(ArchiveError, match="finite"):
        validate_archive(path)


def test_rejects_integer_anchor_outside_finite_coordinate_range(tmp_path):
    path = tmp_path / "oversized-anchor.dancepkg"
    dance = _document().to_json()
    dance["root"]["children"][0]["anchor"][0] = 10**400
    _write_package(
        path,
        _manifest(),
        dance,
        {
            "figures/Atomic.json": _atomic(addons={"Hands": {}}),
            "figures/Composite.json": _composite(),
        },
    )

    with pytest.raises(ArchiveError, match="finite"):
        validate_archive(path)


@pytest.mark.parametrize(
    ("nested_groups", "should_fail"),
    [(123, False), (124, True)],
)
def test_enforces_canonical_tree_depth_boundary(tmp_path, nested_groups, should_fail):
    path = tmp_path / f"depth-{nested_groups}.dancepkg"
    dance = _document().to_json()
    root = dance["root"]
    for index in range(nested_groups):
        root = {
            "type": "group",
            "id": f"nested-{index}",
            "kind": "series",
            "children": [root],
        }
    dance["root"] = root
    _write_package(
        path,
        _manifest(),
        dance,
        {
            "figures/Atomic.json": _atomic(addons={"Hands": {}}),
            "figures/Composite.json": _composite(),
        },
    )

    if should_fail:
        with pytest.raises(ArchiveError, match="nesting depth"):
            validate_archive(path)
    else:
        assert validate_archive(path).document.metadata["name"] == "Archive test"


@pytest.mark.parametrize(
    "member",
    [
        "../escape.json",
        "/absolute.json",
        "figures/../../escape.json",
        "assets//logo.bin",
        "assets/./logo.bin",
    ],
)
def test_rejects_unsafe_archive_member_paths(tmp_path, member):
    path = tmp_path / "unsafe.dancepkg"
    _write_package(
        path,
        _manifest(),
        _document().to_json(),
        {
            "figures/Atomic.json": _atomic(addons={"Hands": {}}),
            "figures/Composite.json": _composite(),
            member: {},
        },
    )
    with pytest.raises(ArchiveError, match="unsafe|path"):
        validate_archive(path)


def test_rejects_archive_over_compressed_source_limit_before_opening(tmp_path, monkeypatch):
    path = tmp_path / "source-too-large.dancepkg"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("package.json", "{}")
    content = path.read_bytes()
    monkeypatch.setattr(archive_module, "_MAX_ARCHIVE_BYTES", len(content) - 1)
    monkeypatch.setattr(
        archive_module.zipfile,
        "ZipFile",
        lambda *args, **kwargs: pytest.fail("oversized archive was opened"),
    )

    with pytest.raises(ArchiveError, match="compressed archive size"):
        validate_archive(content)
    with pytest.raises(ArchiveError, match="compressed archive size"):
        validate_archive(path)


@pytest.mark.parametrize(
    ("members", "compression", "limits", "message"),
    [
        (
            {"assets/large.bin": b"x" * 9},
            zipfile.ZIP_STORED,
            {"_MAX_MEMBER_BYTES": 8},
            "member size",
        ),
        (
            {"assets/a.bin": b"x" * 8, "assets/b.bin": b"y" * 8},
            zipfile.ZIP_STORED,
            {"_MAX_TOTAL_UNCOMPRESSED_BYTES": 15},
            "total uncompressed size",
        ),
        (
            {"assets/a": b"a", "assets/b": b"b", "assets/c": b"c"},
            zipfile.ZIP_STORED,
            {"_MAX_MEMBER_COUNT": 2},
            "member count",
        ),
        (
            {"assets/expanded.bin": b"x" * 1000},
            zipfile.ZIP_DEFLATED,
            {"_MAX_COMPRESSION_RATIO": 2},
            "compression ratio",
        ),
    ],
)
def test_rejects_archive_resource_limits_before_reading_members(
    tmp_path, monkeypatch, members, compression, limits, message
):
    path = tmp_path / "resource-limit.dancepkg"
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    for name, value in limits.items():
        monkeypatch.setattr(archive_module, name, value)
    monkeypatch.setattr(
        archive_module,
        "_read_archive_member",
        lambda *args, **kwargs: pytest.fail("oversized member was read"),
    )

    with pytest.raises(ArchiveError, match=message):
        validate_archive(path)


def test_rejects_definition_mismatch_and_invalid_occurrence_addons(tmp_path):
    path = tmp_path / "bad-definition.dancepkg"
    manifest = _manifest()
    manifest["figures"] = {"Atomic": "figures/Atomic.json", "Composite": "figures/Composite.json"}
    _write_package(
        path,
        manifest,
        _document().to_json(),
        {
            "figures/Atomic.json": _atomic("Different"),
            "figures/Composite.json": _composite(),
        },
    )
    with pytest.raises(ArchiveError, match="Atomic"):
        validate_archive(path)

    bad_doc = _document().to_json()
    bad_doc["root"]["children"][0]["addons"] = ["NotSupported"]
    path2 = tmp_path / "bad-addon.dancepkg"
    _write_package(
        path2,
        _manifest(),
        bad_doc,
        {
            "figures/Atomic.json": _atomic(addons={"Hands": {}}),
            "figures/Composite.json": _composite(),
        },
    )
    with pytest.raises(ArchiveError, match="root.children\\[0\\]"):
        validate_archive(path2)


def test_incomplete_archive_preserves_only_explicit_unresolved_references(tmp_path):
    draft = DanceDocument(
        1,
        {"name": "Draft"},
        GroupNode(
            "root",
            "series",
            (
                FigureOccurrence("available", "Atomic", (0, 0), ()),
                FigureOccurrence("missing", "Missing", (1, 0), ("KeepMe",)),
            ),
        ),
        incomplete=True,
        unresolved_references=("Missing",),
    )
    path = export_archive(
        draft,
        _repository(tmp_path),
        tmp_path / "draft.dancepkg",
        package_id="draft",
    )
    package = validate_archive(path)

    assert package.document.incomplete is True
    assert package.document.unresolved_references == ("Missing",)
    assert package.executable is False
    assert "Missing" not in package.figures

    broken = tmp_path / "not-explicit.dancepkg"
    dance_json = draft.to_json()
    _write_package(
        broken,
        _manifest(figures={"Atomic": "figures/Atomic.json"}),
        dance_json,
        {"figures/Atomic.json": _atomic()},
    )
    with pytest.raises(ArchiveError, match="unresolved"):
        validate_archive(broken)
