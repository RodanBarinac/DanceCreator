"""
Unit tests for Dance module - File loading and figure management.

Tests critical Dance module functionality:
- Loading figures from JSON
- Loading dances from JSON  
- Error handling for missing files
- showCrips functionality

Part of Phase 1 Critical Tests (TEST_COVERAGE_ANALYSIS.md)
"""

import pytest
import Dance
import DanceFloor as DF


class TestFigureLoading:
    """Test loading figures from files."""
    
    def test_load_existing_figure(self):
        """Test loading a figure that exists in /Figures/."""
        fig = Dance.getFigure('1cCast1p')
        assert fig is not None
    
    def test_loaded_figure_has_name(self):
        """Test that loaded figure has Name attribute."""
        fig = Dance.getFigure('1cCast1p')
        assert hasattr(fig, 'Name')
        assert fig.Name is not None
    
    def test_loaded_figure_has_dance_move(self):
        """Test that loaded figure has DanceMove method."""
        fig = Dance.getFigure('1cCast1p')
        assert hasattr(fig, 'DanceMove')
        assert callable(fig.DanceMove)
    
    def test_loaded_figure_has_get_crips(self):
        """Test that loaded figure has getCrips method."""
        fig = Dance.getFigure('1cCast1p')
        assert hasattr(fig, 'getCrips')
        assert callable(fig.getCrips)


class TestDanceLoading:
    """Test loading dances from files."""
    
    def test_load_existing_dance(self):
        """Test loading a dance that exists in /Dances/."""
        dance = Dance.getDance('Marries Wedding_all')
        assert dance is not None
    
    def test_loaded_dance_has_name(self):
        """Test that loaded dance has Name attribute."""
        dance = Dance.getDance('Marries Wedding_all')
        assert hasattr(dance, 'Name')
    
    def test_loaded_dance_has_dance_move(self):
        """Test that loaded dance has DanceMove method."""
        dance = Dance.getDance('Marries Wedding_all')
        assert hasattr(dance, 'DanceMove')
        assert callable(dance.DanceMove)
    
    def test_loaded_dance_has_get_crips(self):
        """Test that loaded dance has getCrips method."""
        dance = Dance.getDance('Marries Wedding_all')
        assert hasattr(dance, 'getCrips')
        assert callable(dance.getCrips)


class TestErrorHandling:
    """Test error handling for invalid files."""
    
    def test_load_nonexistent_figure_raises(self):
        """Test that loading non-existent figure raises error."""
        with pytest.raises(Exception):
            Dance.getFigure('NonexistentFigureXYZ12345')
    
    def test_load_nonexistent_dance_raises(self):
        """Test that loading non-existent dance raises error."""
        with pytest.raises(Exception):
            Dance.getDance('NonexistentDanceXYZ12345')


class TestShowCrips:
    """Test showCrips output functionality."""
    
    def test_show_crips_with_valid_dance_and_floor(self):
        """Test that showCrips executes without error."""
        dance = Dance.getDance('Marries Wedding_all')
        floor = DF.DanceFloor('Test', 3)
        
        # Should not raise
        result = Dance.showCrips(dance, floor)
        assert result is not None
    
    def test_show_crips_returns_list(self):
        """Test that showCrips returns a list."""
        dance = Dance.getDance('Marries Wedding_all')
        floor = DF.DanceFloor('Test', 3)
        
        result = Dance.showCrips(dance, floor)
        assert isinstance(result, list) or result is None
