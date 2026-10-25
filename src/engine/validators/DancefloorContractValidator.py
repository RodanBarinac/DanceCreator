"""
Dancefloor Contract Validator

This module provides validation and serialization utilities to ensure
all dancefloor data conforms to the official contract schema.

The contract is defined in:
- DANCEFLOOR_RENDERER_CONTRACT.md (specification)
- dancefloor_contract.schema.json (JSON Schema)
"""

import json
import os
from typing import Dict, Any, Tuple, List
import jsonschema

from src.engine.models.DanceFloor import default_facing_target


class DancefloorContractError(Exception):
    """Base exception for dancefloor contract violations."""
    pass


class DancefloorValidator:
    """Validates dancefloor data against the contract schema."""

    def __init__(self):
        """Initialize validator by loading the schema."""
        schema_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            '..',
            'schema',
            'dancefloor_contract.schema.json'
        )
        
        if not os.path.exists(schema_path):
            raise FileNotFoundError(
                f"Schema file not found: {schema_path}\n"
                "Make sure schema/dancefloor_contract.schema.json exists in project root."
            )
        
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)

    def validate(self, dancefloor_data: Dict[str, Any]) -> None:
        """
        Validate dancefloor data against the contract schema.

        Args:
            dancefloor_data: The dancefloor data to validate

        Raises:
            DancefloorContractError: If validation fails
            ValueError: If data is not a dict
            TypeError: If data types don't match schema
        """
        if not isinstance(dancefloor_data, dict):
            raise ValueError("Dancefloor data must be a dictionary")

        try:
            jsonschema.validate(
                instance=dancefloor_data,
                schema=self.schema
            )
        except jsonschema.ValidationError as e:
            raise DancefloorContractError(
                f"Dancefloor data violates contract: {e.message}\n"
                f"Path: {'.'.join(str(p) for p in e.absolute_path)}\n"
                f"Schema path: {'.'.join(str(p) for p in e.absolute_schema_path)}"
            ) from e
        except jsonschema.SchemaError as e:
            raise DancefloorContractError(
                f"Schema error: {e.message}"
            ) from e

    def get_validation_errors(self, dancefloor_data: Dict[str, Any]) -> List[str]:
        """
        Get all validation errors without raising exceptions.

        Args:
            dancefloor_data: The dancefloor data to validate

        Returns:
            List of error messages, empty if valid
        """
        errors = []
        validator = jsonschema.Draft7Validator(self.schema)
        
        for error in validator.iter_errors(dancefloor_data):
            path = '.'.join(str(p) for p in error.absolute_path) or 'root'
            errors.append(f"{path}: {error.message}")
        
        return errors


class DancefloorSerializer:
    """Serializes Python objects to contract-conforming dancefloor JSON."""

    @staticmethod
    def serialize_dancefloor(
        name: str,
        couples: int,
        tick: int,
        dancer_map: Dict[Tuple[int, int], Tuple[Any, Any]]
    ) -> Dict[str, Any]:
        """
        Serialize a dancefloor to contract-conforming JSON.

        This method takes the internal representation from DanceFloor.py
        and converts it to the contract schema format.

        Args:
            name: Name of the dancefloor state
            couples: Number of couples
            tick: Current bar/tick
            dancer_map: Map of (row, col) -> (Dancer, facing_coords)
                       where facing_coords is [target_row, target_col]

        Returns:
            Dictionary conforming to dancefloor_contract.schema.json

        Raises:
            DancefloorContractError: If serialized data violates contract
        """
        positions = {}

        for (row, col), (dancer, facing) in dancer_map.items():
            row = int(row) if float(row).is_integer() else row
            col = int(col) if float(col).is_integer() else col
            
            # Side positions retain the conventional couple labels.
            if col == -1:
                position_key = f"{row}m"
            elif col == 1:
                position_key = f"{row}w"
            else:
                position_key = f"{row}:{col}"

            # Extract dancer information
            dancer_name = getattr(dancer, 'name', f'{row}{("mw"[col % 2])}')
            dancer_gender = getattr(dancer, 'gender', '').upper()
            
            # Ensure gender is M or F
            if isinstance(dancer_gender, str):
                gender_lower = dancer_gender.lower()
                if gender_lower.startswith('m'):
                    dancer_gender = 'M'
                elif gender_lower.startswith('f'):
                    dancer_gender = 'F'
                else:
                    # Default based on position
                    dancer_gender = 'M' if col < 0 else 'F'

            # Convert facing to list if needed
            if isinstance(facing, (list, tuple)) and len(facing) >= 2:
                facing_coords = [facing[0], facing[1]]
            else:
                # Facing is a same-row target on the opposite line.
                facing_coords = default_facing_target((row, col))

            positions[position_key] = {
                'dancer': {
                    'name': str(dancer_name),
                    'gender': dancer_gender
                },
                'coord': [row, col],
                'facing': facing_coords
            }

        # Assemble the dancefloor object
        dancefloor = {
            'name': str(name),
            'couples': int(couples),
            'tick': int(tick),
            'positions': positions
        }

        # Validate before returning
        validator = DancefloorValidator()
        validator.validate(dancefloor)

        return dancefloor


# Global validator instance (lazy-loaded)
_validator = None


def get_validator() -> DancefloorValidator:
    """Get or create the global validator instance."""
    global _validator
    if _validator is None:
        _validator = DancefloorValidator()
    return _validator


def validate_dancefloor(dancefloor_data: Dict[str, Any]) -> None:
    """
    Validate dancefloor data using the global validator.

    Args:
        dancefloor_data: The data to validate

    Raises:
        DancefloorContractError: If validation fails
    """
    get_validator().validate(dancefloor_data)


def serialize_dancer(dancer_obj: Any) -> Dict[str, str]:
    """
    Serialize a single dancer object.

    Args:
        dancer_obj: A Dancer object from Dancer.py

    Returns:
        Dictionary with 'name' and 'gender' keys
    """
    gender = getattr(dancer_obj, 'gender', '').lower()
    
    if gender.startswith('m'):
        gender_letter = 'M'
    elif gender.startswith('f'):
        gender_letter = 'F'
    else:
        gender_letter = gender.upper()[0] if gender else 'M'

    return {
        'name': str(getattr(dancer_obj, 'name', '')),
        'gender': gender_letter
    }


# Example usage for integration tests
if __name__ == '__main__':
    # Test with a valid example
    valid_dancefloor = {
        'name': 'Test Floor',
        'couples': 2,
        'tick': 0,
        'positions': {
            '1m': {
                'dancer': {'name': '1m', 'gender': 'M'},
                'coord': [1, -1],
                'facing': [1, 1]
            },
            '1w': {
                'dancer': {'name': '1w', 'gender': 'F'},
                'coord': [1, 1],
                'facing': [1, -1]
            },
            '2m': {
                'dancer': {'name': '2m', 'gender': 'M'},
                'coord': [2, -1],
                'facing': [2, 1]
            },
            '2w': {
                'dancer': {'name': '2w', 'gender': 'F'},
                'coord': [2, 1],
                'facing': [2, -1]
            }
        }
    }

    validator = DancefloorValidator()
    
    try:
        validator.validate(valid_dancefloor)
        print("[OK] Valid dancefloor data passes validation")
    except DancefloorContractError as e:
        print(f"[FAIL] Validation failed: {e}")

    # Test with an invalid example (missing 'facing')
    invalid_dancefloor = {
        'name': 'Invalid Floor',
        'couples': 1,
        'tick': 0,
        'positions': {
            '1m': {
                'dancer': {'name': '1m', 'gender': 'M'},
                'coord': [1, -1]
                # Missing 'facing' - this should fail
            }
        }
    }

    errors = validator.get_validation_errors(invalid_dancefloor)
    if errors:
        print(f"[OK] Invalid data detected {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
    else:
        print("[FAIL] Expected validation to fail but it passed")
