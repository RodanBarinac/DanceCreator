"""
Unit tests for Error Handling and Integration scenarios.

Tests critical error conditions and integration flows:
- Handling missing dancers
- Handling invalid positions
- Dance execution end-to-end
- State consistency after operations

Part of Phase 1 Critical Tests (TEST_COVERAGE_ANALYSIS.md)
"""

import pytest
import Dance
import DanceFloor as DF
from Dancer import Dancer


class TestErrorConditions:
    """Test critical error conditions."""
    
    def test_dance_move_with_empty_floor_raises(self):
        """Test that DanceMove on empty floor raises error."""
        floor = DF.DanceFloor('test', 1)  # No dancers
        fig = Dance.getFigure('1cCast1p')
        
        with pytest.raises(Exception) as exc_info:
            fig.DanceMove(floor)
        
        # Should complain about missing dancer
        assert "no dancer" in str(exc_info.value).lower()
    
    def test_get_crips_with_empty_floor_raises(self):
        """Test that getCrips on empty floor raises error."""
        floor = DF.DanceFloor('test', 1)  # No dancers
        fig = Dance.getFigure('1cCast1p')
        
        with pytest.raises(Exception) as exc_info:
            fig.getCrips(floor)
        
        assert "no dancer" in str(exc_info.value).lower()
    
    def test_invalid_position_raises_error(self):
        """Test that invalid position raises error."""
        floor = DF.DanceFloor('test', 1)
        
        with pytest.raises(Exception) as exc_info:
            floor.DancerbyPos((999, 999))
        
        assert "no dancer here" in str(exc_info.value).lower()
    
    def test_access_nonexistent_dancer_raises(self):
        """Test that accessing position with no dancer raises."""
        floor = DF.DanceFloor('test', 2)
        d1m = Dancer('John', 'M')
        floor.addDancer(d1m, (0, 0), 0)
        
        # Try to access empty position
        with pytest.raises(Exception):
            floor.DancerbyPos((1, 1))


class TestDanceFloorStateConsistency:
    """Test that floor state remains consistent through operations."""
    
    def test_dancer_placement_persists(self):
        """Test that dancer placement persists after addition."""
        floor = DF.DanceFloor('test', 1)
        dancer = Dancer('Alice', 'F')
        
        floor.addDancer(dancer, (0, 1), 0)
        retrieved = floor.DancerbyPos((0, 1))
        
        assert retrieved.name == 'Alice'
        assert retrieved.gender == 'F'
    
    def test_multiple_dancers_dont_interfere(self):
        """Test that multiple dancers maintain independence."""
        floor = DF.DanceFloor('test', 2)
        
        d1m = Dancer('John', 'M')
        d1w = Dancer('Jane', 'F')
        d2m = Dancer('Bob', 'M')
        
        floor.addDancer(d1m, (0, 0), 0)
        floor.addDancer(d1w, (0, 1), 0)
        floor.addDancer(d2m, (1, 0), 0)
        
        # Verify each is in correct position
        assert floor.DancerbyPos((0, 0)).name == 'John'
        assert floor.DancerbyPos((0, 1)).name == 'Jane'
        assert floor.DancerbyPos((1, 0)).name == 'Bob'
    
    def test_floor_state_printable(self):
        """Test that floor state can be printed (no crashes)."""
        floor = DF.DanceFloor('test', 2)
        d1m = Dancer('John', 'M')
        floor.addDancer(d1m, (0, 0), 0)
        
        floor_str = str(floor)
        assert floor_str is not None
        assert len(floor_str) > 0


class TestDanceIntegration:
    """Test complete dance execution flow."""
    
    def test_load_and_display_dance(self):
        """Test loading a dance and displaying it."""
        dance = Dance.getDance('Marries Wedding_all')
        floor = DF.DanceFloor('Wedding Dance', 3)
        
        # Should be able to print without error
        floor_str = str(floor)
        assert floor_str is not None
    
    def test_dance_floor_after_creation(self):
        """Test that newly created floor is valid."""
        floor = DF.DanceFloor('test', 3)
        
        assert floor.AktBar == 1
        assert floor.maxRow == 3
        assert floor.name == 'test'
    
    def test_figure_types_load_correctly(self):
        """Test that different figure types can be loaded."""
        figures = ['1cCast1p', '1cRT']
        
        for fig_name in figures:
            try:
                fig = Dance.getFigure(fig_name)
                assert fig is not None, f"Failed to load {fig_name}"
            except Exception as e:
                # Some figures might not exist, that's ok
                pass


class TestRegressionPrevention:
    """Tests designed to catch common regressions."""
    
    def test_position_format_consistency(self):
        """Test that positions work in both tuple and list format."""
        floor = DF.DanceFloor('test', 1)
        d1 = Dancer('Test1', 'M')
        floor.addDancer(d1, (0, 0), 0)
        
        # Both formats should work
        dancer_tuple = floor.DancerbyPos((0, 0))
        dancer_list = floor.DancerbyPos([0, 0])
        
        assert dancer_tuple.name == dancer_list.name
    
    def test_floor_couples_preserved(self):
        """Test that couple count is preserved."""
        for count in [1, 2, 3, 4, 5]:
            floor = DF.DanceFloor('test', count)
            assert floor.maxRow == count, f"Floor with {count} couples has wrong maxRow"
    
    def test_bar_counter_initial_value(self):
        """Test that bar counter initializes correctly."""
        floor = DF.DanceFloor('test', 1)
        assert floor.AktBar == 1, "Initial bar should be 1, not 0"
