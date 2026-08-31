"""
API Schema Validation Tests

Tests that validate all API endpoints return schema-compliant responses.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from engine.validators.ApiResponseValidator import ApiResponseValidator, ApiResponseValidationError


@pytest.fixture
def validator():
    """Create API response validator instance."""
    return ApiResponseValidator()


@pytest.fixture
def sample_figure_list_response():
    """Sample valid figure list response."""
    return {
        "status": "ok",
        "version": "1",
        "timestamp": "2026-08-31T08:00:00Z",
        "count": 2,
        "total": 10,
        "offset": 0,
        "limit": 100,
        "filters_applied": {},
        "figures": [
            {
                "key": "H1DR",
                "file": "H1DR.json",
                "Name": "Half Diagonal Reel",
                "Desc": "Half Diagonal Reel on the first diagonal",
                "Formation": "reel",
                "Bars": 4,
                "Version": 2
            },
            {
                "key": "TRH",
                "file": "TRH.json",
                "Name": "Turn Right Hand",
                "Desc": "Turn with right hand",
                "Formation": "turn",
                "Bars": 2,
                "Version": 1
            }
        ]
    }


@pytest.fixture
def sample_dance_tree_response():
    """Sample valid dance tree response."""
    return {
        "status": "ok",
        "version": "1",
        "timestamp": "2026-08-31T08:00:00Z",
        "format": "jstree",
        "dance": {
            "file": "TestDance.json",
            "Name": "Test Dance",
            "Desc": "A test dance",
            "shape": "3/32",
            "Version": 3
        },
        "tree": {
            "id": "root",
            "text": "Test Dance",
            "children": [
                {
                    "id": "node-0",
                    "text": "H1DR",
                    "children": [],
                    "type": "figure",
                    "data": {
                        "figureName": "H1DR",
                        "anchor": [1, 1],
                        "addons": [],
                        "original": [[1, 1], ["H1DR"]]
                    }
                }
            ],
            "data": {
                "figureName": "Test Dance",
                "version": 3,
                "original": []
            }
        }
    }


class TestApiResponseValidator:
    """Test API response validator initialization and basic operations."""
    
    def test_validator_initializes_successfully(self):
        """Test that validator can initialize."""
        validator = ApiResponseValidator()
        assert validator is not None
        assert os.path.exists(validator.schema_dir)
    
    def test_validator_loads_schema(self, validator):
        """Test that validator can load schemas."""
        schema = validator.load_schema('api_figures_list.schema.json')
        assert schema is not None
        assert 'properties' in schema
        assert 'required' in schema
    
    def test_validator_caches_schemas(self, validator):
        """Test that validator caches loaded schemas."""
        schema1 = validator.load_schema('api_figures_list.schema.json')
        schema2 = validator.load_schema('api_figures_list.schema.json')
        assert schema1 is schema2  # Same object
    
    def test_validator_raises_on_missing_schema(self, validator):
        """Test that validator raises error for missing schema."""
        with pytest.raises(FileNotFoundError):
            validator.load_schema('nonexistent_schema.json')


class TestFigureListResponseValidation:
    """Test validation of figure list API responses."""
    
    def test_valid_figure_list_response_passes(self, validator, sample_figure_list_response):
        """Test that valid figure list response passes validation."""
        # Should not raise
        validator.validate_figure_list_response(sample_figure_list_response)
    
    def test_figure_list_missing_required_field_fails(self, validator, sample_figure_list_response):
        """Test that missing required fields fail validation."""
        del sample_figure_list_response['status']
        
        with pytest.raises(ApiResponseValidationError) as exc_info:
            validator.validate_figure_list_response(sample_figure_list_response)
        
        assert 'status' in str(exc_info.value).lower()
    
    def test_figure_list_wrong_type_fails(self, validator, sample_figure_list_response):
        """Test that wrong types fail validation."""
        sample_figure_list_response['count'] = "not a number"
        
        with pytest.raises(ApiResponseValidationError):
            validator.validate_figure_list_response(sample_figure_list_response)
    
    def test_figure_list_invalid_status_fails(self, validator, sample_figure_list_response):
        """Test that invalid status values fail validation."""
        sample_figure_list_response['status'] = "error"  # Only "ok" is allowed
        
        with pytest.raises(ApiResponseValidationError):
            validator.validate_figure_list_response(sample_figure_list_response)
    
    def test_figure_list_negative_count_fails(self, validator, sample_figure_list_response):
        """Test that negative count fails validation."""
        sample_figure_list_response['count'] = -1
        
        with pytest.raises(ApiResponseValidationError):
            validator.validate_figure_list_response(sample_figure_list_response)
    
    def test_figure_list_invalid_limit_fails(self, validator, sample_figure_list_response):
        """Test that limit > 1000 fails validation."""
        sample_figure_list_response['limit'] = 2000
        
        with pytest.raises(ApiResponseValidationError):
            validator.validate_figure_list_response(sample_figure_list_response)
    
    def test_figure_list_empty_figures_array_passes(self, validator, sample_figure_list_response):
        """Test that empty figures array is valid."""
        sample_figure_list_response['figures'] = []
        sample_figure_list_response['count'] = 0
        
        # Should not raise
        validator.validate_figure_list_response(sample_figure_list_response)
    
    def test_figure_summary_missing_required_field_fails(self, validator, sample_figure_list_response):
        """Test that figure summary missing required field fails."""
        del sample_figure_list_response['figures'][0]['key']
        
        with pytest.raises(ApiResponseValidationError) as exc_info:
            validator.validate_figure_list_response(sample_figure_list_response)
        
        assert 'key' in str(exc_info.value).lower()


class TestDanceTreeResponseValidation:
    """Test validation of dance tree API responses."""
    
    def test_valid_dance_tree_response_passes(self, validator, sample_dance_tree_response):
        """Test that valid dance tree response passes validation."""
        # Should not raise
        validator.validate_dance_tree_response(sample_dance_tree_response)
    
    def test_dance_tree_missing_id_fails(self, validator, sample_dance_tree_response):
        """Test that missing id fails validation."""
        del sample_dance_tree_response['tree']['id']
        
        with pytest.raises(ApiResponseValidationError):
            validator.validate_dance_tree_response(sample_dance_tree_response)
    
    def test_dance_tree_missing_text_fails(self, validator, sample_dance_tree_response):
        """Test that missing text fails validation."""
        del sample_dance_tree_response['tree']['text']
        
        with pytest.raises(ApiResponseValidationError):
            validator.validate_dance_tree_response(sample_dance_tree_response)
    
    def test_dance_tree_empty_children_valid(self, validator, sample_dance_tree_response):
        """Test that empty children array is valid."""
        sample_dance_tree_response['tree']['children'] = []
        
        # Should not raise
        validator.validate_dance_tree_response(sample_dance_tree_response)
    
    def test_dance_tree_nested_structure_valid(self, validator, sample_dance_tree_response):
        """Test that nested tree structure is valid."""
        sample_dance_tree_response['tree']['children'][0]['children'] = [
            {
                "id": "node-0-0",
                "text": "Sub Figure",
                "children": [],
                "type": "figure",
                "data": {"figureName": "SubFig", "original": []}
            }
        ]
        
        # Should not raise
        validator.validate_dance_tree_response(sample_dance_tree_response)


class TestGetValidationErrors:
    """Test get_validation_errors method."""
    
    def test_valid_data_returns_empty_errors(self, validator, sample_figure_list_response):
        """Test that valid data returns no errors."""
        schema = validator.load_schema('api_figures_list.schema.json')
        errors = validator.get_validation_errors(sample_figure_list_response, schema)
        
        assert errors == []
    
    def test_invalid_data_returns_errors(self, validator, sample_figure_list_response):
        """Test that invalid data returns error messages."""
        del sample_figure_list_response['status']
        schema = validator.load_schema('api_figures_list.schema.json')
        errors = validator.get_validation_errors(sample_figure_list_response, schema)
        
        assert len(errors) > 0
        assert any('status' in err.lower() for err in errors)


class TestIsValid:
    """Test is_valid convenience method."""
    
    def test_is_valid_returns_true_for_valid_data(self, validator, sample_figure_list_response):
        """Test that is_valid returns True for valid data."""
        result = validator.is_valid(sample_figure_list_response, 'api_figures_list.schema.json')
        assert result is True
    
    def test_is_valid_returns_false_for_invalid_data(self, validator, sample_figure_list_response):
        """Test that is_valid returns False for invalid data."""
        del sample_figure_list_response['status']
        result = validator.is_valid(sample_figure_list_response, 'api_figures_list.schema.json')
        assert result is False
    
    def test_is_valid_returns_false_for_nonexistent_schema(self, validator, sample_figure_list_response):
        """Test that is_valid returns False for missing schema."""
        result = validator.is_valid(sample_figure_list_response, 'nonexistent.schema.json')
        assert result is False


class TestDancefloorResponseValidation:
    """Test validation of dancefloor contract responses."""
    
    def test_valid_dancefloor_response_passes(self, validator):
        """Test that valid dancefloor response passes validation."""
        dancefloor_data = {
            "name": "Initial Setup",
            "couples": 3,
            "tick": 0,
            "positions": {
                "1m": {
                    "dancer": {"name": "John", "gender": "M"},
                    "coord": [1, 1],
                    "facing": [1, 2]  # Facing coordinates, not direction string
                },
                "1w": {
                    "dancer": {"name": "Jane", "gender": "F"},
                    "coord": [1, 2],
                    "facing": [1, 1]  # Facing coordinates, not direction string
                }
            }
        }
        
        # Should not raise
        validator.validate_dancefloor_response(dancefloor_data)
    
    def test_dancefloor_missing_required_field_fails(self, validator):
        """Test that missing required field fails."""
        dancefloor_data = {
            "name": "Test",
            "tick": 0,
            # Missing 'couples'
            "positions": {
                "1m": {
                    "dancer": {"name": "John", "gender": "M"},
                    "coord": [1, 1],
                    "facing": "S"
                }
            }
        }
        
        with pytest.raises(ApiResponseValidationError):
            validator.validate_dancefloor_response(dancefloor_data)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
