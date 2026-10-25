import pytest

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    FigureOccurrence,
    GroupNode,
)
from src.engine.editing.commands import (
    CreateGroup,
    DeleteNode,
    EditCommandError,
    InsertOccurrence,
    MoveNode,
    ReorderNode,
    UpdateAddons,
    UpdateAnchor,
    apply_command,
)
from src.engine.editing.proposals import create_proposal


class _FakeRepository:
    def __init__(self, definitions):
        self.definitions = definitions

    def figure_exists(self, figure_ref):
        return figure_ref in self.definitions

    def get_legacy_definition(self, figure_ref):
        return self.definitions[figure_ref]


def _catalog_repository():
    return _FakeRepository(
        {
            "AtomicV2": {"Version": 2, "Name": "Atomic"},
            "NestedV3": {
                "Version": 3,
                "FigureList": ["s", [[[3, 4], "AtomicV2"]]],
            },
            "OuterV3": {
                "Version": 3,
                "FigureList": [
                    "p",
                    [
                        [[1, 2], "AtomicV2"],
                        [[5, 6], "NestedV3"],
                    ],
                ],
            },
            "UnresolvedV3": {
                "Version": 3,
                "FigureList": ["s", [[[7, 8], "MissingNested"]]],
            },
        }
    )


def _figure(node_id, figure_ref="1cWait", anchor=(0, 0), addons=()):
    return FigureOccurrence(node_id, figure_ref, anchor, addons)


def _document(root):
    return DanceDocument(1, {"name": "editing"}, root)


def _position(document, node_id):
    def walk(node, path=()):
        if node.id == node_id:
            return path
        if isinstance(node, GroupNode):
            for index, child in enumerate(node.children):
                found = walk(child, path + (index,))
                if found is not None:
                    return found
        elif isinstance(node, CompositeOccurrence):
            return walk(node.root, path + ("root",))
        return None

    return walk(document.root)


def test_insert_occurrence_allocates_stable_id_and_places_it_at_requested_index():
    document = _document(
        GroupNode("root", "series", (_figure("left"), _figure("right")))
    )

    candidate = apply_command(
        document,
        InsertOccurrence("root", "1cWait", 1, anchor=(2, 3)),
        repository=_FakeRepository({"1cWait": {"Version": 2}}),
    )
    inserted = candidate.root.children[1]

    assert isinstance(inserted, FigureOccurrence)
    assert inserted.id not in {"root", "left", "right"}
    assert inserted.figure_ref == "1cWait"
    assert inserted.anchor == (2, 3)
    assert candidate.revision == document.revision
    assert candidate.root.children[0] is document.root.children[0]

    moved = apply_command(candidate, ReorderNode(inserted.id, 2))
    assert moved.root.children[2].id == inserted.id
    proposal = create_proposal(moved, MoveNode(inserted.id, "root", 0), moved.revision)
    assert proposal.candidate.root.children[0].id == inserted.id


def test_reorder_is_limited_to_siblings_in_a_series_group():
    document = _document(
        GroupNode(
            "root",
            "series",
            (
                GroupNode("parallel", "parallel", (_figure("left"), _figure("right"))),
                _figure("tail"),
            ),
        )
    )

    with pytest.raises(EditCommandError) as error:
        apply_command(document, ReorderNode("left", 1))

    assert error.value.code == "reorder_requires_series"
    assert document.root.children[0].children[0].id == "left"


def test_insert_occurrence_is_limited_to_series_groups():
    document = _document(
        GroupNode("root", "series", (GroupNode("parallel", "parallel", ()),))
    )

    with pytest.raises(EditCommandError) as error:
        apply_command(
            document,
            InsertOccurrence("parallel", "1cWait", 0),
            repository=_FakeRepository({"1cWait": {"Version": 2}}),
        )

    assert error.value.code == "insert_requires_series"
    assert document.root.children[0].children == ()


def test_delete_removes_an_occurrence_but_never_root_or_group():
    document = _document(
        GroupNode("root", "series", (_figure("first"), GroupNode("nested", "series", ())))
    )

    candidate = apply_command(document, DeleteNode("first"))
    assert candidate.root.children == (document.root.children[1],)

    for node_id in ("root", "nested"):
        with pytest.raises(EditCommandError) as error:
            apply_command(document, DeleteNode(node_id))
        assert error.value.code == "delete_requires_occurrence"


def test_move_occurrence_preserves_anchor_and_rejects_groups_and_invalid_destinations():
    occurrence = _figure("moving", anchor=(4, -2))
    document = _document(
        GroupNode(
            "root",
            "series",
            (
                GroupNode("from", "series", (occurrence,)),
                GroupNode("to", "parallel", ()),
            ),
        )
    )

    moved = apply_command(document, MoveNode("moving", "to", 0))
    assert moved.root.children[0].children == ()
    assert moved.root.children[1].children[0] == occurrence
    assert moved.root.children[1].children[0].anchor == (4, -2)

    for node_id in ("root", "from"):
        with pytest.raises(EditCommandError) as error:
            apply_command(document, MoveNode(node_id, "to", 0))
        assert error.value.code == "move_requires_occurrence"
    with pytest.raises(EditCommandError) as error:
        apply_command(document, MoveNode("moving", "missing", 0))
    assert error.value.code == "destination_not_found"


def test_update_anchor_and_addons_preserve_unchanged_occurrences():
    original = _figure("first", addons=("E2c",))
    sibling = _figure("sibling")
    document = _document(GroupNode("root", "series", (original, sibling)))

    anchored = apply_command(document, UpdateAnchor("first", (1.5, 2)))
    assert anchored.root.children[0] == _figure("first", anchor=(1.5, 2), addons=("E2c",))
    assert anchored.root.children[1] is sibling

    updated = apply_command(anchored, UpdateAddons("first", ()))
    assert updated.root.children[0] == _figure("first", anchor=(1.5, 2))
    assert updated.root.children[1] is sibling


def test_create_group_adds_a_new_series_or_parallel_without_converting_existing_groups():
    document = _document(GroupNode("root", "series", (_figure("first"),)))

    candidate = apply_command(document, CreateGroup("root", "parallel", 0))

    assert candidate.root.kind == "series"
    assert candidate.root.children[0].kind == "parallel"
    assert candidate.root.children[0].children == ()
    assert candidate.root.children[1].id == "first"
    assert candidate.root.children[0].id != "root"


def test_commands_reject_invalid_indices_and_composite_addons_without_mutation():
    composite = CompositeOccurrence(
        "composite", "V3Figure", (0, 0), (), GroupNode("embedded", "series", ())
    )
    document = _document(GroupNode("root", "series", (composite,)))
    before = document.to_json()

    with pytest.raises(EditCommandError) as index_error:
        apply_command(
            document,
            InsertOccurrence("root", "1cWait", 2),
            repository=_FakeRepository({"1cWait": {"Version": 2}}),
        )
    assert index_error.value.code == "invalid_index"

    with pytest.raises(EditCommandError) as addon_error:
        apply_command(document, UpdateAddons("composite", ("addon",)))
    assert addon_error.value.code == "composite_addons_unsupported"
    assert document.to_json() == before


def test_proposal_is_a_structural_projection_and_does_not_validate_or_execute(monkeypatch):
    document = _document(GroupNode("root", "series", ()))

    monkeypatch.setattr(
        "src.engine.editing.proposals.validate_document",
        lambda *args, **kwargs: pytest.fail("proposal creation must not validate"),
        raising=False,
    )
    monkeypatch.setattr(
        "src.engine.editing.proposals.execute_document",
        lambda *args, **kwargs: pytest.fail("proposal creation must not execute"),
        raising=False,
    )

    proposal = create_proposal(
        document,
        InsertOccurrence("root", "1cWait", 0),
        base_revision=0,
        repository=_FakeRepository({"1cWait": {"Version": 2}}),
    )

    assert proposal.candidate.root.children[0].figure_ref == "1cWait"
    assert proposal.base_revision == document.revision
    assert proposal.structural_tree["id"] == "root"
    assert "trace" not in proposal.structural_tree
    assert not hasattr(proposal, "trace")


def test_insert_occurrence_resolves_atomic_and_composite_catalog_definitions():
    repository = _catalog_repository()
    document = _document(GroupNode("root", "series", ()))

    candidate = apply_command(
        document,
        InsertOccurrence("root", "AtomicV2", 0, anchor=(9, 10)),
        repository=repository,
    )
    atomic = candidate.root.children[0]
    assert isinstance(atomic, FigureOccurrence)
    assert atomic.figure_ref == "AtomicV2"
    assert atomic.anchor == (9, 10)

    candidate = apply_command(
        document,
        InsertOccurrence("root", "OuterV3", 0, anchor=(11, 12)),
        repository=repository,
    )
    composite = candidate.root.children[0]
    assert isinstance(composite, CompositeOccurrence)
    assert composite.figure_ref == "OuterV3"
    assert composite.anchor == (11, 12)
    assert composite.root.kind == "parallel"
    first, nested = composite.root.children
    assert isinstance(first, FigureOccurrence)
    assert first.figure_ref == "AtomicV2"
    assert first.anchor == (1, 2)
    assert isinstance(nested, CompositeOccurrence)
    assert nested.figure_ref == "NestedV3"
    assert nested.anchor == (5, 6)
    nested_child = nested.root.children[0]
    assert isinstance(nested_child, FigureOccurrence)
    assert nested_child.figure_ref == "AtomicV2"
    assert nested_child.anchor == (3, 4)
    assert candidate.incomplete is False


def test_insert_rejects_missing_catalog_entries_and_malformed_composites():
    repository = _catalog_repository()
    repository.definitions["BrokenV3"] = {
        "Version": 3,
        "FigureList": ["series", "not a child list"],
    }
    document = _document(GroupNode("root", "series", ()))

    with pytest.raises(EditCommandError) as missing:
        apply_command(
            document,
            InsertOccurrence("root", "Missing", 0),
            repository=repository,
        )
    assert missing.value.code == "reference_not_found"

    with pytest.raises(EditCommandError) as malformed:
        apply_command(
            document,
            InsertOccurrence("root", "BrokenV3", 0),
            repository=repository,
        )
    assert malformed.value.code == "invalid_composite_definition"
    assert document.root.children == ()


def test_repeated_composite_proposals_have_fresh_ids_stable_through_reads_and_apply():
    repository = _catalog_repository()
    document = _document(GroupNode("root", "series", ()))
    command = InsertOccurrence("root", "OuterV3", 0)

    first = create_proposal(document, command, document.revision, repository=repository)
    second = create_proposal(document, command, document.revision, repository=repository)
    first_occurrence = first.candidate.root.children[0]
    second_occurrence = second.candidate.root.children[0]

    def ids(node):
        result = [node.id]
        if isinstance(node, GroupNode):
            for child in node.children:
                result.extend(ids(child))
        elif isinstance(node, CompositeOccurrence):
            result.extend(ids(node.root))
        return result

    first_ids = ids(first_occurrence)
    second_ids = ids(second_occurrence)
    assert len(first_ids) == len(set(first_ids))
    assert len(second_ids) == len(set(second_ids))
    assert set(first_ids).isdisjoint(second_ids)
    assert ids(first.candidate.root.children[0]) == first_ids


def test_unresolved_nested_composite_reference_is_preserved_and_marks_candidate_incomplete():
    candidate = apply_command(
        _document(GroupNode("root", "series", ())),
        InsertOccurrence("root", "UnresolvedV3", 0),
        repository=_catalog_repository(),
    )

    composite = candidate.root.children[0]
    assert isinstance(composite, CompositeOccurrence)
    nested = composite.root.children[0]
    assert isinstance(nested, FigureOccurrence)
    assert nested.figure_ref == "MissingNested"
    assert nested.anchor == (7, 8)
    assert candidate.incomplete is True
    assert candidate.unresolved_references == ("MissingNested",)


def test_insert_proposal_requires_repository_and_preserves_composite_addons():
    document = _document(GroupNode("root", "series", ()))

    with pytest.raises(EditCommandError) as error:
        create_proposal(document, InsertOccurrence("root", "AtomicV2", 0), 0)
    assert error.value.code == "repository_required"

    proposal = create_proposal(
        document,
        InsertOccurrence("root", "OuterV3", 0, addons=("unsupported",)),
        0,
        repository=_catalog_repository(),
    )
    composite = proposal.candidate.root.children[0]
    assert isinstance(composite, CompositeOccurrence)
    assert composite.addons == ("unsupported",)
