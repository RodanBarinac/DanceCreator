import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep

import pytest

from src.engine.domain.dance_model import DanceDocument, FigureOccurrence, GroupNode
from src.engine.figures.capabilities import FigureRepository
from src.engine.persistence.archive import (
    ArchiveCollisionError,
    ArchiveError,
    ArchiveStore,
    ArchiveTransactionError,
    export_archive,
)


def _figure(name, desc):
    return {
        "Name": name,
        "Desc": desc,
        "Version": 2,
        "Bars": 1,
        "Addons": {},
    }


def _document(name, figure_ref="Step", revision=0):
    return DanceDocument(
        1,
        {"name": name},
        GroupNode("root", "series", (FigureOccurrence("step", figure_ref, (0, 0), ()),)),
        revision=revision,
    )


def _package(tmp_path, name="Portable", figure_name="Step", desc="portable"):
    figures = tmp_path / f"source-{desc}"
    figures.mkdir()
    (figures / f"{figure_name}.json").write_text(
        json.dumps(_figure(figure_name, desc)), encoding="utf-8"
    )
    source_repo = FigureRepository(figures, tmp_path / "unused-dances")
    path = tmp_path / f"{desc}.dancepkg"
    export_archive(
        _document(name, figure_name),
        source_repo,
        path,
        package_id=f"package-{desc}",
    )
    return path


def _tree_bytes(directory):
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def test_invalid_package_is_rejected_before_store_creates_any_persistent_files(tmp_path):
    invalid = tmp_path / "invalid.dancepkg"
    invalid.write_bytes(b"not a zip")
    store_root = tmp_path / "store"

    with pytest.raises(ArchiveError):
        ArchiveStore(store_root).import_archive(invalid)

    assert not store_root.exists()


def test_copy_collision_creates_isolated_package_namespace_and_scoped_repository(tmp_path):
    package = _package(tmp_path)
    store = ArchiveStore(tmp_path / "store")
    first = store.import_archive(package)
    original_bytes = _tree_bytes(first.path)

    copied = store.import_archive(
        package, collision="copy", copy_name="Portable Copy"
    )

    assert copied.path != first.path
    assert first.document.metadata["name"] == "Portable"
    assert copied.document.metadata["name"] == "Portable Copy"
    assert _tree_bytes(first.path) == original_bytes
    assert copied.repository.figure_directory == (copied.path / "figures").resolve()
    assert copied.repository.get_legacy_definition("Step")["Desc"] == "portable"
    assert "Figures" not in str(copied.path)


def test_copy_collision_requires_a_unique_name_and_does_not_overwrite(tmp_path):
    package = _package(tmp_path)
    store = ArchiveStore(tmp_path / "store")
    first = store.import_archive(package)

    with pytest.raises(ArchiveCollisionError, match="copy_name"):
        store.import_archive(package, collision="copy")
    with pytest.raises(ArchiveCollisionError, match="already exists"):
        store.import_archive(package, collision="copy", copy_name="Portable")

    copied = store.import_archive(
        package, collision="copy", copy_name="Portable Copy"
    )
    with pytest.raises(ArchiveCollisionError, match="already exists"):
        store.import_archive(package, collision="copy", copy_name="portable copy")
    assert store.get(first.dance_id).document.metadata["name"] == "Portable"
    assert store.get(copied.dance_id).document.metadata["name"] == "Portable Copy"


def test_concurrent_copy_imports_cannot_create_duplicate_names(tmp_path):
    package = _package(tmp_path)
    root = tmp_path / "store"
    ArchiveStore(root).import_archive(package)
    stores = [ArchiveStore(root), ArchiveStore(root)]
    for store in stores:
        original_find = store._find_by_name

        def delayed_find(name, original_find=original_find):
            result = original_find(name)
            if name.casefold() == "concurrent copy":
                sleep(0.05)
            return result

        store._find_by_name = delayed_find

    start = Barrier(2)

    def import_copy(store):
        start.wait()
        try:
            return store.import_archive(
                package, collision="copy", copy_name="Concurrent Copy"
            )
        except ArchiveCollisionError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(import_copy, stores))

    assert sum(isinstance(result, ArchiveCollisionError) for result in results) == 1
    assert sum(not isinstance(result, ArchiveCollisionError) for result in results) == 1
    assert len(list((root / "dances").iterdir())) == 2


def test_scoped_repository_never_falls_back_to_shared_catalog_for_package_references(tmp_path):
    package = _package(tmp_path)
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "Step.json").write_text(json.dumps(_figure("Step", "shared")), encoding="utf-8")
    store = ArchiveStore(tmp_path / "store", shared_figure_directory=shared)
    imported = store.import_archive(package)

    assert imported.repository.get_legacy_definition("Step")["Desc"] == "portable"
    with pytest.raises(FileNotFoundError):
        imported.repository.get_legacy_definition("NotBundled")


@pytest.mark.parametrize(
    ("member", "change", "message"),
    [
        (
            "package.json",
            lambda data: data.update(formatVersion=99),
            "formatVersion",
        ),
        (
            "package.json",
            lambda data: data.update(figures={}),
            "reference",
        ),
        (
            "figures/Step.json",
            lambda data: data.update(Version=99),
            "Version",
        ),
        (
            "dance.json",
            lambda data: data["root"]["children"][0].update(addons=["Unknown"]),
            "addons",
        ),
        (
            "dance.json",
            lambda data: data.update(status="incomplete"),
            "unresolved|status",
        ),
    ],
)
def test_get_rejects_stored_packages_that_fail_full_validation(
    tmp_path, member, change, message
):
    store = ArchiveStore(tmp_path / "store")
    imported = store.import_archive(_package(tmp_path))
    stored_member = imported.path / member
    data = json.loads(stored_member.read_text(encoding="utf-8"))
    change(data)
    stored_member.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ArchiveError, match=message):
        store.get(imported.dance_id)


def test_replace_requires_confirmation_and_keeps_timestamped_unpruned_backups(tmp_path):
    root = tmp_path / "store"
    store = ArchiveStore(root)
    original = store.import_archive(_package(tmp_path, desc="original"))
    original_bytes = _tree_bytes(original.path)
    incoming = _package(tmp_path, desc="replacement")

    with pytest.raises(ArchiveCollisionError, match="confirm"):
        store.import_archive(incoming, collision="replace")
    assert _tree_bytes(original.path) == original_bytes

    replaced = store.import_archive(
        incoming, collision="replace", confirm_replace=True
    )
    backups = list((root / "backups").rglob("dance.json"))
    assert len(backups) == 1
    backup_root = backups[0].parent
    assert _tree_bytes(backup_root) == original_bytes
    assert replaced.path == original.path
    assert replaced.repository.get_legacy_definition("Step")["Desc"] == "replacement"

    second = _package(tmp_path, desc="replacement-again")
    store.import_archive(second, collision="replace", confirm_replace=True)
    assert len(list((root / "backups").rglob("dance.json"))) == 2
    assert any(
        files == original_bytes
        for files in (_tree_bytes(path.parent) for path in (root / "backups").rglob("dance.json"))
    )


def test_replace_can_preserve_a_higher_canonical_revision_transactionally(tmp_path):
    store = ArchiveStore(tmp_path / "store")
    original = store.import_archive(_package(tmp_path, desc="revision-original"))
    incoming = _package(tmp_path, desc="revision-incoming")

    replaced = store.import_archive(
        incoming,
        collision="replace",
        confirm_replace=True,
        expected_revision=original.document.revision,
        replacement_revision=4,
    )

    assert replaced.document.revision == 4
    current_bytes = _tree_bytes(replaced.path)
    with pytest.raises(ArchiveCollisionError, match="replacement_revision"):
        store.import_archive(
            incoming,
            collision="replace",
            confirm_replace=True,
            expected_revision=4,
            replacement_revision=4,
        )
    assert _tree_bytes(replaced.path) == current_bytes


def test_replace_with_missing_expected_target_does_not_import_as_a_new_dance(tmp_path):
    store = ArchiveStore(tmp_path / "store")

    with pytest.raises(ArchiveCollisionError, match="target does not exist"):
        store.import_archive(
            _package(tmp_path),
            collision="replace",
            confirm_replace=True,
            expected_revision=0,
        )

    assert not store.dances_directory.exists()


@pytest.mark.parametrize("failure_point", ["after_stage", "before_swap", "after_backup", "after_swap"])
def test_failure_during_stage_or_swap_leaves_existing_package_byte_for_byte_intact(
    tmp_path, failure_point
):
    root = tmp_path / "store"
    store = ArchiveStore(root)
    existing = store.import_archive(_package(tmp_path, desc="old"))
    before = _tree_bytes(existing.path)

    def inject(point):
        if point == failure_point:
            raise OSError(f"injected at {point}")

    incoming = _package(tmp_path, desc="new")
    failing_store = ArchiveStore(root, failure_injector=inject)
    with pytest.raises(ArchiveTransactionError, match="injected"):
        failing_store.import_archive(
            incoming, collision="replace", confirm_replace=True
        )

    assert _tree_bytes(existing.path) == before
    assert not any(path.name.startswith(".staging-") for path in root.iterdir())


def test_imported_package_writes_do_not_touch_shared_figure_catalog(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    shared_file = shared / "Step.json"
    shared_file.write_text(json.dumps(_figure("Step", "shared")), encoding="utf-8")
    before = shared_file.read_bytes()
    imported = ArchiveStore(
        tmp_path / "store", shared_figure_directory=shared
    ).import_archive(_package(tmp_path, desc="private"))

    assert shared_file.read_bytes() == before
    assert imported.repository.figure_directory != shared.resolve()


@pytest.mark.parametrize("failure_point", ["after_backup", "after_swap"])
def test_unexpected_injected_failure_is_propagated_after_rollback(tmp_path, failure_point):
    store = ArchiveStore(tmp_path / "store")
    existing = store.import_archive(_package(tmp_path, desc="old"))
    before = _tree_bytes(existing.path)

    def inject(point):
        if point == failure_point:
            raise RuntimeError("unexpected injected failure")

    with pytest.raises(RuntimeError, match="unexpected injected failure"):
        ArchiveStore(
            tmp_path / "store", failure_injector=inject
        ).import_archive(
            _package(tmp_path, desc="incoming"),
            collision="replace",
            confirm_replace=True,
        )

    assert _tree_bytes(existing.path) == before
