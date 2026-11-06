import pytest
from timeutil.duration import parse_duration

OK = [("1h30m", 5400), ("2d", 172800), ("45s", 45), ("1d2h3m4s", 93784), ("1h 30m", 5400),
      ("  1H30M ", 5400), ("90", 90), ("0s", 0), ("0", 0), ("365d", 31536000), ("1D 1S", 86401),
      ("1h   2m", 3720), ("10m", 600)]
BAD = ["", "   ", "1x", "h", "-5s", "1.5h", "30m1h", "1h2h", "1h30", "366d", "365d1s", "abc", "1h-30m"]


@pytest.mark.parametrize("s,v", OK)
def test_ok(s, v):
    assert parse_duration(s) == v
    assert type(parse_duration(s)) is int


@pytest.mark.parametrize("s", BAD)
def test_bad(s):
    with pytest.raises(ValueError):
        parse_duration(s)


@pytest.mark.parametrize("v", [None, 5, b"1h"])
def test_type(v):
    with pytest.raises(TypeError):
        parse_duration(v)
