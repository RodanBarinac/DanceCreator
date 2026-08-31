"""
Tests for write API request schemas.
Validates that request body schemas correctly accept/reject payloads.
"""

import json
import pytest
from src.engine.validators.ApiResponseValidator import ApiResponseValidator


class TestDanceUpdateRequestSchema:
    """Test api_dance_update_request.schema.json"""
    
    def test_valid_dance_update_payload(self):
        """Valid dance update payload passes validation"""
        validator = ApiResponseValidator()
        
        valid_payload = {
            "Name": "Test Dance",
            "Desc": "A test dance for validation",
            "shape": "3/32",
            "FigureList": ["s", [
                [[1, 1], "H1DR"],
                [[2, 1], "H2DR"]
            ]],
            "Version": 3
        }
        
        errors = validator.get_validation_errors('api_dance_update_request.schema.json', valid_payload)
        assert len(errors) == 0, f"Valid payload should pass: {errors}"
    
    def test_missing_required_field_fails(self):
        """Dance update without required field fails validation"""
        validator = ApiResponseValidator()
        
        invalid_payload = {
            "Name": "Test Dance",
            "Desc": "Missing FigureList",
            "Version": 3
            # Missing FigureList
        }
        
        errors = validator.get_validation_errors('api_dance_update_request.schema.json', invalid_payload)
        assert len(errors) > 0
        assert any("FigureList" in str(e) for e in errors)
    
    def test_invalid_version_fails(self):
        """Dance with wrong version fails validation"""
        validator = ApiResponseValidator()
        
        invalid_payload = {
            "Name": "Test Dance",
            "Desc": "Wrong version",
            "shape": "3/32",
            "FigureList": ["s", []],
            "Version": 2  # Should be 3
        }
        
        errors = validator.get_validation_errors('api_dance_update_request.schema.json', invalid_payload)
        assert len(errors) > 0
        assert any("Version" in str(e) or "const" in str(e) for e in errors)
    
    def test_invalid_shape_pattern_fails(self):
        """Dance with invalid shape pattern fails"""
        validator = ApiResponseValidator()
        
        invalid_payload = {
            "Name": "Test Dance",
            "Desc": "Bad shape",
            "shape": "invalid/shape",  # Should be digits/digits
            "FigureList": ["s", []],
            "Version": 3
        }
        
        errors = validator.get_validation_errors('api_dance_update_request.schema.json', invalid_payload)
        assert len(errors) > 0


class TestDanceCreateRequestSchema:
    """Test api_dance_create_request.schema.json"""
    
    def test_valid_dance_create_payload(self):
        """Valid dance create payload passes validation"""
        validator = ApiResponseValidator()
        
        valid_payload = {
            "Name": "New Dance",
            "Desc": "A newly created dance",
            "shape": "4/48",
            "FigureList": ["p", [
                [[1, 1], "1cCast1p"],
                [[2, 1], "1cLT"]
            ]],
            "Version": 3
        }
        
        errors = validator.get_validation_errors('api_dance_create_request.schema.json', valid_payload)
        assert len(errors) == 0, f"Valid create payload should pass: {errors}"


class TestDanceTreeUpdateRequestSchema:
    """Test api_dance_tree_update_request.schema.json"""
    
    def test_valid_tree_update_payload(self):
        """Valid jsTree update payload passes validation"""
        validator = ApiResponseValidator()
        
        valid_payload = {
            "tree": {
                "id": "root",
                "text": "Test Dance",
                "type": "root",
                "data": {},
                "children": [
                    {
                        "id": "fig1",
                        "text": "H1DR",
                        "type": "figure",
                        "data": {
                            "figureName": "H1DR",
                            "anchor": [1, 1],
                            "addons": []
                        }
                    }
                ]
            }
        }
        
        errors = validator.get_validation_errors('api_dance_tree_update_request.schema.json', valid_payload)
        assert len(errors) == 0, f"Valid tree payload should pass: {errors}"
    
    def test_missing_tree_key_fails(self):
        """Tree update without 'tree' key fails"""
        validator = ApiResponseValidator()
        
        invalid_payload = {
            "data": {"some": "data"}  # Missing 'tree' key
        }
        
        errors = validator.get_validation_errors('api_dance_tree_update_request.schema.json', invalid_payload)
        assert len(errors) > 0
    
    def test_invalid_node_type_fails(self):
        """Tree node with invalid type fails"""
        validator = ApiResponseValidator()
        
        invalid_payload = {
            "tree": {
                "id": "root",
                "text": "Test",
                "type": "invalid_type",  # Should be figure, group, or root
                "data": {}
            }
        }
        
        errors = validator.get_validation_errors('api_dance_tree_update_request.schema.json', invalid_payload)
        assert len(errors) > 0


class TestFigureUpdateRequestSchema:
    """Test api_figure_update_request.schema.json"""
    
    def test_valid_atomic_figure_update(self):
        """Valid atomic figure update passes validation"""
        validator = ApiResponseValidator()
        
        valid_payload = {
            "Name": "TestFigure",
            "Desc": "A test figure",
            "Formation": "turn",
            "Version": 2,
            "Addons": {},
            "Bars": 4,
            "StartPos": [[0, 0], [0, 2]],
            "EndPos": [[1, 0], [1, 2]],
            "CriptDesc": ["Dancer 1 turns", "Dancer 2 turns"]
        }
        
        errors = validator.get_validation_errors('api_figure_update_request.schema.json', valid_payload)
        assert len(errors) == 0, f"Valid atomic figure should pass: {errors}"
    
    def test_valid_complex_figure_update(self):
        """Valid complex figure update passes validation"""
        validator = ApiResponseValidator()
        
        valid_payload = {
            "Name": "ComplexFigure",
            "Desc": "A complex figure",
            "Formation": "reel",
            "Version": 1,
            "FigureList": [
                {"type": "subfigure", "name": "H1DR"},
                {"type": "subfigure", "name": "H2DR"}
            ]
        }
        
        errors = validator.get_validation_errors('api_figure_update_request.schema.json', valid_payload)
        assert len(errors) == 0, f"Valid complex figure should pass: {errors}"
    
    def test_atomic_with_figurelist_fails(self):
        """Figure with both atomic and complex fields fails"""
        validator = ApiResponseValidator()
        
        invalid_payload = {
            "Name": "BadFigure",
            "Desc": "Has both types of fields",
            "Formation": "turn",
            "Version": 2,
            "Addons": {},
            "Bars": 4,
            "StartPos": [[0, 0]],
            "EndPos": [[1, 0]],
            "CriptDesc": ["Turn"],
            "FigureList": ["subfig"]  # Can't have both!
        }
        
        errors = validator.get_validation_errors('api_figure_update_request.schema.json', invalid_payload)
        assert len(errors) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
