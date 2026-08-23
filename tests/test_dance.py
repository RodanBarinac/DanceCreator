import Dance
import DanceFloor as DF


def test_get_figure():
    """Test loading a figure by name."""
    f = Dance.getFigure('1cCast1p')
    assert f is not None
    assert hasattr(f, 'DanceMove'), "Figure should have DanceMove method"


def test_get_dance():
    """Test loading a dance by name."""
    d = Dance.getDance('Marries Wedding_all')
    assert d is not None
    assert hasattr(d, 'DanceMove'), "Dance should have DanceMove method"


def test_dancefloor_creation():
    """Test creating a dance floor with multiple couples."""
    floor = DF.DanceFloor('Test Floor', 3)
    assert floor is not None
    assert floor.maxRow == 3
    assert floor.AktBar == 1


def test_figure_dance_move():
    """Test that a figure's DanceMove method exists and is callable."""
    floor = DF.DanceFloor('test', 1)
    f = Dance.getFigure('1cCast1p')
    
    # Verify the method exists and is callable
    assert hasattr(f, 'DanceMove'), "Figure should have DanceMove method"
    assert callable(f.DanceMove), "DanceMove should be callable"
