"""
Unit tests for Dance module - File loading and figure management.

Tests critical Dance module functionality:
- Loading figures from JSON
- Loading dances from JSON  
- Error handling for missing files
- showCrips functionality

Part of Phase 1 Critical Tests (TEST_COVERAGE_ANALYSIS.md)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from engine.models import Dance
from engine.models import DanceFloor as DF


class TestFigureLoading:
    """Test loading figures from files."""
    
    def test_load_existing_figure(self):
        """Test loading a figure that exists in data/Figures/."""
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
        """Test loading a dance that exists in data/Dances/."""
        dance = Dance.getDance('Marries Wedding_all')
        assert dance is not None
    
    def test_loaded_dance_has_name(self):
        """Test that the loaded dance exposes its canonical name."""
        dance = Dance.getDance('Marries Wedding_all')
        assert dance.name == 'Marries Wedding'
        assert dance.name.strip()
    
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
    """Test structured, non-printing instruction data."""

    def test_show_crips_returns_lines_without_printing(self, capsys):
        dance = Dance.getDance('Marries Wedding_all')
        floor = DF.DanceFloor('Test', 3)

        result = Dance.showCrips(dance, floor)

        assert result
        assert all(set(line) == {"figureRef", "dancer", "barRange", "text"} for line in result)
        assert any(line["text"] and "turns right hand" in line["text"] for line in result)
        assert capsys.readouterr().out == ""
