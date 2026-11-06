from timeutil.duration import parse_duration


def test_basic():
    assert parse_duration("1h30m") == 5400
