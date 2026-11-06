from billing.report import format_krw


def test_krw():
    assert format_krw(1500) == "1,500원"
