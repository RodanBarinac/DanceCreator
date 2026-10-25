"""Tests for converting jsTree payloads into dance FigureList data."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import GUI_DanceCreator_App as app_module
from src.engine.converters.TreeConverter import TreeConversionError, TreeConverter


def root_node(children=None, group_type=None, include_type=True, node_id="root"):
    node = {
        "id": node_id,
        "text": "Dance",
        "children": [] if children is None else children,
        "data": {},
    }
    if include_type:
        node["type"] = "root"
    if group_type is not None:
        node["data"]["groupType"] = group_type
    return node


def group_node(children=None, group_type="s", node_id="group-1", text=None):
    return {
        "id": node_id,
        "text": text or ("Sequential Group" if group_type == "s" else "Parallel Group"),
        "type": "group",
        "children": [] if children is None else children,
        "data": {"groupType": group_type},
    }


def figure_node(
    figure_name="Figure",
    anchor=None,
    addons=None,
    node_id="figure-1",
    text=None,
):
    data = {"figureName": figure_name}
    if anchor is not None:
        data["anchor"] = anchor
    if addons is not None:
        data["addons"] = addons
    return {
        "id": node_id,
        "text": text or figure_name or "Figure",
        "type": "figure",
        "data": data,
    }


class TestTreeConverterSuccess:
    """Successful conversion cases."""

    def test_flat_series_group_converts_children_in_order(self):
        tree = root_node(
            [
                figure_node("A"),
                figure_node("B"),
                figure_node("C", anchor=[2, 1]),
            ]
        )

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [[[1, 0], "A"], [[1, 0], "B"], [[2, 1], "C"]]]

    def test_root_group_type_overrides_default(self):
        tree = root_node([figure_node("A"), figure_node("B")], group_type="p")

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["p", [[[1, 0], "A"], [[1, 0], "B"]]]

    def test_root_without_group_type_defaults_to_series(self):
        tree = root_node([figure_node("Only")])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result[0] == "s"

    def test_nested_groups_convert_recursively(self):
        tree = root_node(
            [
                group_node(
                    [
                        figure_node("Lead", anchor=[1, 0]),
                        group_node(
                            [figure_node("Mirror"), figure_node("Support", addons=["Hands"])],
                            group_type="p",
                            node_id="group-inner",
                        ),
                    ],
                    group_type="s",
                    node_id="group-outer",
                )
            ]
        )

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == [
            "s",
            [[
                "s",
                [
                    [[1, 0], "Lead"],
                    ["p", [[[1, 0], "Mirror"], [[1, 0], ["Support", ["Hands"]]]]],
                ],
            ]],
        ]

    def test_group_node_can_be_empty(self):
        tree = root_node([group_node([], group_type="p")])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [["p", []]]]

    def test_figure_anchor_is_preserved(self):
        tree = root_node([figure_node("AnchorFigure", anchor=[4, 0])])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [[[4, 0], "AnchorFigure"]]]

    def test_missing_anchor_defaults_to_one_based_origin(self):
        tree = root_node([figure_node("DefaultAnchor")])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [[[1, 0], "DefaultAnchor"]]]

    def test_invalid_anchor_values_are_normalized_like_frontend(self):
        tree = root_node([figure_node("Normalized", anchor=[0, -9])])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [[[1, -9], "Normalized"]]]

    def test_float_anchor_values_are_coerced_to_integers(self):
        tree = root_node([figure_node("FloatAnchor", anchor=[3.9, 1.1])])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [[[3, 1], "FloatAnchor"]]]

    def test_non_array_anchor_falls_back_to_default(self):
        tree = root_node([figure_node("BadAnchor", anchor="not-an-array")])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [[[1, 0], "BadAnchor"]]]

    def test_figure_with_addons_emits_name_and_addon_pair(self):
        tree = root_node([figure_node("Decorated", addons=["Hands", "Turn"])])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [[[1, 0], ["Decorated", ["Hands", "Turn"]]]]]

    def test_figure_with_empty_addons_emits_plain_string_target(self):
        tree = root_node([figure_node("Plain", addons=[])])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [[[1, 0], "Plain"]]]

    def test_existing_get_tree_addons_shape_is_flattened(self):
        tree = root_node([figure_node("Flattened", addons=[["Wave"]])])

        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == ["s", [[[1, 0], ["Flattened", ["Wave"]]]]]

    def test_existing_get_tree_root_without_type_round_trips_single_group(self):
        dance = {
            "Name": "Round Trip",
            "Desc": "Test dance",
            "shape": "3/32",
            "FigureList": ["s", [[[1, 0], ["Decorated", ["Hands"]]], ["p", [[[2, 0], ["Side", ["Turn"]]]]]]],
            "Version": 3,
        }

        tree = app_module.build_dance_tree(dance, dance["Name"])
        result = TreeConverter.jstree_to_figure_list(tree)

        assert result == dance["FigureList"]

    def test_round_trip_helper_returns_true_for_nested_dance(self):
        dance = {
            "Name": "Nested",
            "Desc": "Round trip helper",
            "shape": "4/40",
            "FigureList": [
                "p",
                [
                    [[1, -1], "Lead"],
                    ["s", [[[2, -1], ["Trail", ["Cross"]]], [[3, -1], "Finish"]]],
                ],
            ],
            "Version": 3,
        }

        assert TreeConverter.validate_round_trip(dance) is True

    def test_round_trip_helper_treats_empty_addon_list_as_equivalent(self):
        dance = {
            "Name": "Empty Addons",
            "Desc": "Schema-compatible empty addons",
            "shape": "3/32",
            "FigureList": ["s", [[[1, -1], ["Simple", []]]]],
            "Version": 3,
        }

        assert TreeConverter.validate_round_trip(dance) is True


class TestTreeConverterErrors:
    """Error handling and guards."""

    def test_missing_figure_name_raises(self):
        tree = root_node([figure_node(None, node_id="bad-figure")])
        tree["children"][0]["data"].pop("figureName")

        with pytest.raises(TreeConversionError, match="figureName"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_blank_figure_name_raises(self):
        tree = root_node([figure_node("   ", node_id="blank-figure")])

        with pytest.raises(TreeConversionError, match="figureName"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_group_missing_group_type_raises(self):
        bad_group = group_node([figure_node("A")], node_id="group-missing")
        bad_group["data"].pop("groupType")
        tree = root_node([bad_group])

        with pytest.raises(TreeConversionError, match="groupType"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_group_invalid_group_type_raises(self):
        tree = root_node([group_node([figure_node("A")], group_type="x", node_id="group-invalid")])

        with pytest.raises(TreeConversionError, match="groupType"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_root_invalid_group_type_raises(self):
        tree = root_node([figure_node("A")], group_type="x")

        with pytest.raises(TreeConversionError, match="groupType"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_unknown_node_type_raises(self):
        tree = root_node(
            [{"id": "mystery", "text": "Mystery", "type": "mystery", "data": {}, "children": []}]
        )

        with pytest.raises(TreeConversionError, match="Invalid node type"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_invalid_root_type_raises(self):
        tree = root_node([figure_node("A")])
        tree["type"] = "group"

        with pytest.raises(TreeConversionError, match="Invalid root node type"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_group_missing_children_raises(self):
        bad_group = group_node([figure_node("A")], node_id="group-no-children")
        bad_group.pop("children")
        tree = root_node([bad_group])

        with pytest.raises(TreeConversionError, match="children list"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_root_missing_children_raises(self):
        tree = root_node([figure_node("A")])
        tree.pop("children")

        with pytest.raises(TreeConversionError, match="children list"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_non_dict_node_raises(self):
        with pytest.raises(TreeConversionError, match="objects"):
            TreeConverter.jstree_to_figure_list(["not", "a", "dict"])

    def test_non_dict_data_raises(self):
        tree = root_node([figure_node("A")])
        tree["children"][0]["data"] = "not-an-object"

        with pytest.raises(TreeConversionError, match="data must be an object"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_non_list_addons_raises(self):
        tree = root_node([figure_node("A", addons="Hands")])

        with pytest.raises(TreeConversionError, match="addons must be an array"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_non_string_addon_member_raises(self):
        tree = root_node([figure_node("A", addons=["Hands", 3])])

        with pytest.raises(TreeConversionError, match="addons must contain only strings"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_max_depth_guard_raises_before_stack_overflow(self):
        current = figure_node("Bottom")
        for index in range(TreeConverter.MAX_DEPTH + 1):
            current = group_node([current], group_type="s", node_id=f"group-{index}")
        tree = root_node([current])

        with pytest.raises(TreeConversionError, match="Maximum tree depth"):
            TreeConverter.jstree_to_figure_list(tree)

    def test_circular_reference_raises(self):
        cycle = group_node([], group_type="s", node_id="cycle")
        cycle["children"].append(cycle)
        tree = root_node([cycle])

        with pytest.raises(TreeConversionError, match="Circular tree reference"):
            TreeConverter.jstree_to_figure_list(tree)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
