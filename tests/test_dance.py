import Dance
import DanceFloor as DF


def test_get_figure():
    f = Dance.getFigure('1cCast1p')
    assert f is not None


def test_get_dance():
    d = Dance.getDance('Marries_Wedding_full_v3')
    assert d is not None


def test_simple_move_no_error():
    floor = DF.DanceFloor('test', 1)
    f = Dance.getFigure('1cCast1p')
    # Should not raise
    res = f.getCrips(floor)
    assert isinstance(res, list)
