"""
API Response Validator

Provides validation for API responses against JSON schemas.
Ensures all outgoing payloads conform to contract specifications.
"""

import json
import os
from typing import Dict, Any, List, Optional
import jsonschema
from jsonschema import Draft7Validator, validators


class ApiResponseValidationError(Exception):
    """Raised when API response validation fails."""
    def __init__(self, schema_name: str, errors: List[str]):
        self.schema_name = schema_name
        self.errors = errors
        message = f"Response validation failed for {schema_name}:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(message)


class ApiResponseValidator:
    """Validates API responses against JSON schemas."""
    
    def __init__(self, schema_dir: Optional[str] = None):
        """
        Initialize validator with schema directory.
        
        Args:
            schema_dir: Path to schema directory. If None, uses default location.
        """
        if schema_dir is None:
            schema_dir = os.path.join(
                os.path.dirname(__file__),
                '..',
                '..',
                '..',
                'schema'
            )
        
        self.schema_dir = os.path.abspath(schema_dir)
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        
        if not os.path.exists(self.schema_dir):
            raise FileNotFoundError(
                f"Schema directory not found: {self.schema_dir}\n"
                "Make sure the schema/ directory exists in project root."
            )
    
    def load_schema(self, schema_name: str) -> Dict[str, Any]:
        """
        Load a JSON schema file.
        
        Args:
            schema_name: Name of schema file (e.g., 'api_figures_list.schema.json')
            
        Returns:
            Loaded schema dictionary
            
        Raises:
            FileNotFoundError: If schema file doesn't exist
            json.JSONDecodeError: If schema file is invalid JSON
        """
        if schema_name in self._schema_cache:
            return self._schema_cache[schema_name]
        
        schema_path = os.path.join(self.schema_dir, schema_name)
        
        if not os.path.exists(schema_path):
            raise FileNotFoundError(
                f"Schema file not found: {schema_path}\n"
                f"Looking for: {schema_name}"
            )
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        self._schema_cache[schema_name] = schema
        return schema
    
    def validate(self, response_data: Any, schema_name: str) -> None:
        """
        Validate response data against a schema.
        
        Args:
            response_data: The response data to validate
            schema_name: Name of schema file
            
        Raises:
            ApiResponseValidationError: If validation fails
        """
        schema = self.load_schema(schema_name)
        errors = self.get_validation_errors(response_data, schema)
        
        if errors:
            raise ApiResponseValidationError(schema_name, errors)
    
    def get_validation_errors(self, data: Any, schema: Dict[str, Any]) -> List[str]:
        """
        Get all validation errors without raising exceptions.
        
        Args:
            data: Data to validate
            schema: Schema dictionary
            
        Returns:
            List of error messages (empty if valid)
        """
        validator = Draft7Validator(schema)
        errors = []
        
        for error in validator.iter_errors(data):
            path = ' -> '.join(str(p) for p in error.absolute_path) if error.absolute_path else 'root'
            errors.append(f"{path}: {error.message}")
        
        return errors
    
    def is_valid(self, data: Any, schema_name: str) -> bool:
        """
        Check if data is valid without raising exceptions.
        
        Args:
            data: Data to validate
            schema_name: Name of schema file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            schema = self.load_schema(schema_name)
            errors = self.get_validation_errors(data, schema)
            return len(errors) == 0
        except Exception:
            return False
    
    def validate_figure_list_response(self, response: Dict[str, Any]) -> None:
        """Validate GET /api/figures response."""
        self.validate(response, 'api_figures_list.schema.json')
    
    def validate_figure_detail_response(self, response: Dict[str, Any]) -> None:
        """Validate GET /api/figures/<id> response."""
        self.validate(response, 'figure.schema.json')
    
    def validate_dance_list_response(self, response: Dict[str, Any]) -> None:
        """Validate GET /api/dances response."""
        self.validate(response, 'api_dances_list.schema.json')
    
    def validate_dance_tree_response(self, response: Dict[str, Any]) -> None:
        """Validate GET /api/dances/<id>/tree response."""
        self.validate(response, 'api_dance_tree_response.schema.json')
    
    def validate_dancefloor_response(self, response: Dict[str, Any]) -> None:
        """Validate dancefloor init/execute responses."""
        self.validate(response, 'dancefloor_contract.schema.json')


# Convenience singleton instance
_default_validator: Optional[ApiResponseValidator] = None


def get_validator() -> ApiResponseValidator:
    """Get or create the default validator instance."""
    global _default_validator
    if _default_validator is None:
        _default_validator = ApiResponseValidator()
    return _default_validator


def validate_response(data: Any, schema_name: str) -> None:
    """
    Convenience function to validate using default validator.
    
    Args:
        data: Data to validate
        schema_name: Schema file name
        
    Raises:
        ApiResponseValidationError: If validation fails
    """
    get_validator().validate(data, schema_name)
