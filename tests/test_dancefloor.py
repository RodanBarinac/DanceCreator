"""
Unit tests for DanceFloor class - Position Management and Dancer Placement.

Tests critical DanceFloor functionality to prevent regressions:
- Dancer placement and retrieval
- Position validation
- Floor state consistency
- Error handling for invalid positions

Part of Phase 1 Critical Tests (TEST_COVERAGE_ANALYSIS.md)
"""

import pytest
import DanceFloor as DF
from Dancer import Dancer


@pytest.fixture
def empty_floor():
    """Create an empty dance floor with 1 couple."""
    return DF.DanceFloor('test', 1)


@pytest.fixture
def populated_floor():
    """Create a dance floor with dancers in starting positions."""
    floor = DF.DanceFloor('test', 2)
    d1m = Dancer('John', 'M')
    d1w = Dancer('Jane', 'F')
    d2m = Dancer('Bob', 'M')
    d2w = Dancer('Alice', 'F')
    
    floor.DanceFloorMap[(1, 1)][0] = d1m  # 1m position
    floor.DanceFloorMap[(1, 3)][0] = d1w  # 1w position
    floor.DanceFloorMap[(2, 1)][0] = d2m  # 2m position
    floor.DanceFloorMap[(2, 3)][0] = d2w  # 2w position
    return floor


class TestDanceFloorInitialization:
    """Test DanceFloor creation and initialization."""
    
    def test_create_floor_with_name(self):
        """Test creating a dance floor with a name."""
        floor = DF.DanceFloor('My Dance', 3)
        assert floor is not None
        assert floor.name == 'My Dance'
    
    def test_floor_initial_bar_is_one(self):
        """Test that initial bar starts at 1."""
        floor = DF.DanceFloor('test', 1)
        assert floor.AktBar == 1
    
    def test_floor_couples_count(self):
        """Test that maxRow reflects couple count."""
        floor = DF.DanceFloor('test', 3)
        assert floor.maxRow == 3
    
    def test_floor_has_dancefloor_map(self):
        """Test that floor has DanceFloorMap attribute."""
        floor = DF.DanceFloor('test', 1)
        assert hasattr(floor, 'DanceFloorMap')
        assert isinstance(floor.DanceFloorMap, dict)


class TestDancerPlacement:
    """Test adding and retrieving dancers."""
    
    def test_add_dancer_to_floor(self, empty_floor):
        """Test adding a dancer to the floor."""
        dancer = Dancer('Test', 'M')
        empty_floor.addDancer(dancer, (1, 2), 0)
        # Should not raise an error
        assert True
    
    def test_dancer_retrieval_by_position(self, populated_floor):
        """Test retrieving a dancer by position."""
        dancer = populated_floor.DancerbyPos((1, 1))
        assert dancer is not None
        assert dancer.name == 'John'
    
    def test_get_dancer_position_tuple_format(self, populated_floor):
        """Test that DancerbyPos accepts tuple positions."""
        dancer1 = populated_floor.DancerbyPos((1, 1))
        assert dancer1.name == 'John'
    
    def test_get_dancer_position_list_format(self, populated_floor):
        """Test that DancerbyPos accepts list positions."""
        dancer1 = populated_floor.DancerbyPos([1, 1])
        assert dancer1.name == 'John'
    
    def test_dancer_properties_maintained(self, populated_floor):
        """Test that dancer properties are preserved."""
        dancer = populated_floor.DancerbyPos((1, 1))
        assert dancer.name == 'John'
        assert dancer.gender == 'M'


class TestPositionValidation:
    """Test position validation and error handling."""
    
    def test_dancer_not_found_raises_exception(self, empty_floor):
        """Test that accessing non-existent dancer raises exception."""
        with pytest.raises(Exception) as exc_info:
            empty_floor.DancerbyPos((99, 99))
        assert "no dancer here" in str(exc_info.value).lower()
    
    def test_invalid_position_raises_error(self, populated_floor):
        """Test that invalid position raises error."""
        with pytest.raises(Exception) as exc_info:
            populated_floor.DancerbyPos((99, 99))
        assert "no dancer here" in str(exc_info.value).lower()
    
    def test_position_conversion_tuple_to_tuple(self, populated_floor):
        """Test position format conversion works correctly."""
        # Both should return same dancer
        dancer_tuple = populated_floor.DancerbyPos((1, 1))
        dancer_list = populated_floor.DancerbyPos([1, 1])
        assert dancer_tuple.name == dancer_list.name


class TestFloorStateConsistency:
    """Test that floor state remains consistent."""
    
    def test_floor_state_after_adding_dancer(self, empty_floor):
        """Test that floor records dancer after addition."""
        dancer = Dancer('Test', 'M')
        empty_floor.addDancer(dancer, (1, 2), 0)
        
        retrieved = empty_floor.DancerbyPos((1, 2))
        assert retrieved.name == 'Test'
    
    def test_multiple_dancers_independent(self, populated_floor):
        """Test that multiple dancers don't interfere."""
        d1m = populated_floor.DancerbyPos((1, 1))
        d1w = populated_floor.DancerbyPos((1, 3))
        d2m = populated_floor.DancerbyPos((2, 1))
        
        assert d1m.name == 'John'
        assert d1w.name == 'Jane'
        assert d2m.name == 'Bob'
    
    def test_floor_string_representation(self, populated_floor):
        """Test that floor can be converted to string without error."""
        floor_str = str(populated_floor)
        assert floor_str is not None
        assert len(floor_str) > 0
        assert 'Men' in floor_str
        assert 'Lady' in floor_str
        assert '○Joh' in floor_str or '○ohn' in floor_str
        assert '□Jan' in floor_str or '□ane' in floor_str


class TestDanceFloorIntegration:
    """Test DanceFloor integration with other components."""
    
    def test_floor_with_different_couple_counts(self):
        """Test that floor works with different couple counts."""
        for couples in [1, 2, 3, 4]:
            floor = DF.DanceFloor(f'test_{couples}', couples)
            assert floor.maxRow == couples
    
    def test_empty_floor_string_representation(self, empty_floor):
        """Test empty floor can be printed without error."""
        floor_str = str(empty_floor)
        assert floor_str is not None
        assert 'End of Bar' in floor_str
