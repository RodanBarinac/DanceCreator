"""Tests for write-request validation in ApiRequestValidator."""

import pytest

from src.engine.validators.ApiRequestValidator import (
    ApiRequestValidator,
    ApiValidationError,
)


def make_valid_dance_payload():
    return {
        "Name": "Test Dance",
        "Desc": "A complete dance definition",
        "shape": "3/32",
        "FigureList": [
            "s",
            [
                [[1, 0], "H1DR"],
                ["p", [
                    [[2, 0], ["Turn RH", ["fast"]]],
                    [[3, 0], "Circle"]
                ]]
            ]
        ],
        "Version": 3,
    }


def make_valid_tree_payload():
    return {
        "tree": {
            "id": "root",
            "text": "Test Dance",
            "type": "root",
            "data": {},
            "children": [
                {
                    "id": "group-1",
                    "text": "Series",
                    "type": "group",
                    "data": {"groupType": "s"},
                    "children": [
                        {
                            "id": "figure-1",
                            "text": "H1DR",
                            "type": "figure",
                            "data": {
                                "figureName": "H1DR",
                                "anchor": [1, 0],
                                "addons": [],
                            },
                        }
                    ],
                }
            ],
        }
    }


def make_valid_atomic_figure_payload():
    return {
        "Name": "Turn Right Hand",
        "Desc": "Partners turn by the right hand",
        "Formation": "turn",
        "Version": 2,
        "Addons": {},
        "Bars": 4,
        "StartPos": [[0, -1], [0, 1]],
        "EndPos": [[1, -1], [1, 1]],
        "CriptDesc": ["Turn right hand"],
    }


def make_valid_complex_figure_payload():
    return {
        "Name": "Complex Turn",
        "Desc": "Built from smaller figures",
        "Formation": "reel",
        "Version": 1,
        "FigureList": [
            {"type": "subfigure", "name": "H1DR"},
            {"type": "subfigure", "name": "H2DR"},
        ],
    }


def assert_validation_error(callable_obj, expected_field):
    with pytest.raises(ApiValidationError) as exc_info:
        callable_obj()
    assert expected_field in exc_info.value.field or expected_field in str(exc_info.value)


class TestValidateDanceUpdateRequest:
    def test_valid_payload_returns_data_unchanged(self):
        payload = make_valid_dance_payload()

        result = ApiRequestValidator.validate_dance_update_request(payload)

        assert result is payload

    @pytest.mark.parametrize("missing_field", ["Name", "Desc", "FigureList", "Version"])
    def test_missing_required_field_raises(self, missing_field):
        payload = make_valid_dance_payload()
        del payload[missing_field]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            missing_field,
        )

    def test_non_object_body_raises(self):
        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request([]),
            "body",
        )

    def test_name_must_be_non_empty_string(self):
        payload = make_valid_dance_payload()
        payload["Name"] = 123

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "Name",
        )

    def test_desc_must_be_non_empty_string(self):
        payload = make_valid_dance_payload()
        payload["Desc"] = "   "

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "Desc",
        )

    def test_version_must_be_three(self):
        payload = make_valid_dance_payload()
        payload["Version"] = 2

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "Version",
        )

    def test_shape_must_be_string(self):
        payload = make_valid_dance_payload()
        payload["shape"] = 32

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "shape",
        )

    def test_shape_must_match_expected_pattern(self):
        payload = make_valid_dance_payload()
        payload["shape"] = "03/32"

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "shape",
        )

    def test_figure_list_must_be_array(self):
        payload = make_valid_dance_payload()
        payload["FigureList"] = "not-a-list"

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "FigureList",
        )

    def test_figure_list_must_have_two_items(self):
        payload = make_valid_dance_payload()
        payload["FigureList"] = ["s"]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "FigureList",
        )

    def test_figure_list_requires_valid_group_marker(self):
        payload = make_valid_dance_payload()
        payload["FigureList"] = ["x", [[[1, 0], "H1DR"]]]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "FigureList",
        )

    def test_figure_list_elements_must_be_array(self):
        payload = make_valid_dance_payload()
        payload["FigureList"] = ["s", "not-an-array"]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "FigureList",
        )

    def test_figure_list_elements_must_not_be_empty(self):
        payload = make_valid_dance_payload()
        payload["FigureList"] = ["s", []]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "FigureList",
        )

    def test_figure_list_rejects_malformed_figure_call(self):
        payload = make_valid_dance_payload()
        payload["FigureList"] = ["s", [["bad-element"]]]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_update_request(payload),
            "FigureList",
        )


class TestValidateDanceCreateRequest:
    def test_valid_payload_returns_data_unchanged(self):
        payload = make_valid_dance_payload()

        result = ApiRequestValidator.validate_dance_create_request(payload)

        assert result is payload

    @pytest.mark.parametrize("missing_field", ["Name", "Desc", "FigureList", "Version"])
    def test_missing_required_field_raises(self, missing_field):
        payload = make_valid_dance_payload()
        del payload[missing_field]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_create_request(payload),
            missing_field,
        )

    def test_invalid_shape_is_rejected(self):
        payload = make_valid_dance_payload()
        payload["shape"] = "0/32"

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_create_request(payload),
            "shape",
        )

    def test_malformed_figure_list_is_rejected(self):
        payload = make_valid_dance_payload()
        payload["FigureList"] = ["p", [{"bad": "element"}]]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_dance_create_request(payload),
            "FigureList",
        )


class TestValidateTreeUpdateRequest:
    def test_valid_payload_returns_data_unchanged(self):
        payload = make_valid_tree_payload()

        result = ApiRequestValidator.validate_tree_update_request(payload)

        assert result is payload

    def test_non_object_body_raises(self):
        assert_validation_error(
            lambda: ApiRequestValidator.validate_tree_update_request("bad"),
            "body",
        )

    def test_missing_tree_field_raises(self):
        assert_validation_error(
            lambda: ApiRequestValidator.validate_tree_update_request({}),
            "tree",
        )

    def test_tree_must_be_object(self):
        payload = {"tree": []}

        assert_validation_error(
            lambda: ApiRequestValidator.validate_tree_update_request(payload),
            "tree",
        )

    @pytest.mark.parametrize("missing_field", ["id", "text", "type"])
    def test_tree_node_missing_required_field_raises(self, missing_field):
        payload = make_valid_tree_payload()
        del payload["tree"][missing_field]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_tree_update_request(payload),
            f"tree.{missing_field}",
        )

    def test_tree_node_invalid_type_raises(self):
        payload = make_valid_tree_payload()
        payload["tree"]["type"] = "invalid"

        assert_validation_error(
            lambda: ApiRequestValidator.validate_tree_update_request(payload),
            "tree.type",
        )

    def test_tree_node_text_must_be_non_empty(self):
        payload = make_valid_tree_payload()
        payload["tree"]["text"] = "   "

        assert_validation_error(
            lambda: ApiRequestValidator.validate_tree_update_request(payload),
            "tree.text",
        )

    def test_tree_children_must_be_array(self):
        payload = make_valid_tree_payload()
        payload["tree"]["children"] = {}

        assert_validation_error(
            lambda: ApiRequestValidator.validate_tree_update_request(payload),
            "tree.children",
        )

    def test_tree_child_must_be_object(self):
        payload = make_valid_tree_payload()
        payload["tree"]["children"] = ["bad-child"]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_tree_update_request(payload),
            "tree.children[0]",
        )

    def test_nested_children_are_validated_recursively(self):
        payload = make_valid_tree_payload()
        payload["tree"]["children"][0]["children"][0]["type"] = "bad"

        assert_validation_error(
            lambda: ApiRequestValidator.validate_tree_update_request(payload),
            "tree.children[0].children[0].type",
        )


class TestValidateFigureUpdateRequest:
    def test_valid_atomic_payload_returns_data_unchanged(self):
        payload = make_valid_atomic_figure_payload()

        result = ApiRequestValidator.validate_figure_update_request(payload)

        assert result is payload

    def test_valid_complex_payload_returns_data_unchanged(self):
        payload = make_valid_complex_figure_payload()

        result = ApiRequestValidator.validate_figure_update_request(payload)

        assert result is payload

    @pytest.mark.parametrize("missing_field", ["Name", "Desc", "Formation", "Version"])
    def test_missing_common_required_field_raises(self, missing_field):
        payload = make_valid_atomic_figure_payload()
        del payload[missing_field]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            missing_field,
        )

    def test_non_object_body_raises(self):
        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request([]),
            "body",
        )

    def test_name_must_be_non_empty_string(self):
        payload = make_valid_atomic_figure_payload()
        payload["Name"] = 0

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "Name",
        )

    def test_desc_must_be_non_empty_string(self):
        payload = make_valid_atomic_figure_payload()
        payload["Desc"] = ""

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "Desc",
        )

    def test_formation_must_be_non_empty_string(self):
        payload = make_valid_atomic_figure_payload()
        payload["Formation"] = None

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "Formation",
        )

    def test_version_must_be_positive_number(self):
        payload = make_valid_atomic_figure_payload()
        payload["Version"] = 0

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "Version",
        )

    def test_figure_must_be_atomic_or_complex(self):
        payload = {
            "Name": "Incomplete Figure",
            "Desc": "Has no execution content",
            "Formation": "turn",
            "Version": 1,
        }

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "Bars",
        )

    def test_figure_cannot_mix_atomic_and_complex_fields(self):
        payload = make_valid_atomic_figure_payload()
        payload["FigureList"] = [{"type": "subfigure", "name": "H1DR"}]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "FigureList",
        )

    def test_complex_figure_cannot_include_addons_from_atomic_shape(self):
        payload = make_valid_complex_figure_payload()
        payload["Addons"] = {}

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "FigureList",
        )

    @pytest.mark.parametrize(
        "missing_field",
        ["Addons", "Bars", "StartPos", "EndPos", "CriptDesc"],
    )
    def test_atomic_figure_missing_required_atomic_field_raises(self, missing_field):
        payload = make_valid_atomic_figure_payload()
        del payload[missing_field]

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            missing_field,
        )

    def test_atomic_bars_must_be_positive_number(self):
        payload = make_valid_atomic_figure_payload()
        payload["Bars"] = -1

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "Bars",
        )

    def test_complex_figure_requires_figure_list(self):
        payload = make_valid_complex_figure_payload()
        payload["FigureList"] = []

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "FigureList",
        )

    def test_complex_figure_figure_list_must_be_array(self):
        payload = make_valid_complex_figure_payload()
        payload["FigureList"] = "not-a-list"

        assert_validation_error(
            lambda: ApiRequestValidator.validate_figure_update_request(payload),
            "FigureList",
        )
