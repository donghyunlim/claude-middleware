import json, os, pytest
from billing import report

G = json.load(open(os.path.join(os.path.dirname(__file__), "golden.json")))


@pytest.mark.parametrize("f,v,out", G["fmt"])
def test_fmt(f, v, out):
    fn = getattr(report, f)
    if out[0] == "ok":
        assert fn(v) == out[1]
    else:
        with pytest.raises(Exception) as e:
            fn(v)
        assert type(e.value).__name__ == out[1]


@pytest.mark.parametrize("it,c,out", G["lines"])
def test_line(it, c, out):
    if out[0] == "ok":
        assert report.format_line(it, c) == out[1]
    else:
        with pytest.raises(Exception) as e:
            report.format_line(it, c)
        assert type(e.value).__name__ == out[1]
