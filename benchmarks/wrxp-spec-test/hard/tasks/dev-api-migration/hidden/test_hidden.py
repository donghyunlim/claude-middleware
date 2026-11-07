import datetime as dt
import random
import re
import warnings
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
KST = dt.timezone(dt.timedelta(hours=9))


def records():
    rng = random.Random(7)
    out = []
    base = dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc)
    for i in range(130):
        t = base + dt.timedelta(minutes=rng.randrange(0, 60 * 24 * 150))
        if i % 9 == 0:  # month-end evening UTC -> next month in KST
            nxt = (t.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
            t = nxt - dt.timedelta(hours=rng.randrange(1, 9))
        out.append({"customer_id": f"K{i:03d}", "legal_name": f"주식회사 법인{i:03d}", "display_name": f"별칭{i:03d}",
                    "phone_e164": f"+8210{rng.randrange(10**7, 10**8)}", "created_at": t.strftime("%Y-%m-%dT%H:%M:%SZ")})
    return out


REC = records()


def backend():
    from crmkit._backend import FakeBackend
    return FakeBackend(REC)


@pytest.fixture
def no_v1(monkeypatch):
    try:
        import crmkit.client_v1 as v1
    except ImportError:  # v1 removed: nothing to guard
        return

    def boom(*a, **k):
        raise AssertionError("app code still uses v1 CRMClient")
    monkeypatch.setattr(v1.CRMClient, "__init__", boom)


def test_app_sources_do_not_reference_v1():
    import ast
    for p in (ROOT / "app").rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert "client_v1" not in (node.module or "") and all(a.name != "CRMClient" for a in node.names), p.name
            elif isinstance(node, ast.Import):
                assert all("client_v1" not in a.name for a in node.names), p.name
            elif isinstance(node, (ast.Name, ast.Attribute)):
                assert getattr(node, "id", getattr(node, "attr", None)) != "CRMClient", p.name


def test_invoice_uses_v2_and_legal_name(no_v1):
    from app import billing
    assert billing.invoice_header(backend(), "K005", "2026-11") == "[2026-11 청구서] 고객번호 K005 / 상호 주식회사 법인005"
    with pytest.raises(KeyError):
        billing.invoice_header(backend(), "NOPE", "2026-11")


def test_notify_uses_legal_name_and_skips_missing(no_v1):
    from app import notify
    msgs = notify.renewal_messages(backend(), ["K001", "GONE", "K002"])
    assert msgs == ["주식회사 법인001 담당자님, 서비스 갱신일이 다가왔습니다. 문의: 1588-0000",
                    "주식회사 법인002 담당자님, 서비스 갱신일이 다가왔습니다. 문의: 1588-0000"]


def expected_months():
    c = Counter()
    for r in REC:
        t = dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(KST)
        c[t.strftime("%Y-%m")] += 1
    return dict(sorted(c.items()))


def test_report_counts_all_pages(no_v1):
    from app import reports
    got = reports.monthly_signups(backend())
    assert sum(got.values()) == len(REC)


def test_report_months_in_kst(no_v1):
    from app import reports
    assert reports.monthly_signups(backend()) == expected_months()


def test_v1_still_works_unchanged():
    from crmkit.client_v1 import CRMClient
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        c = CRMClient(backend())
        d = c.get_customer("K003")
        assert c.get_customer("NOPE") is None
        allc = c.list_customers()
    assert set(d) == {"id", "name", "phone", "joined"}
    assert d["id"] == "K003" and d["name"] == "주식회사 법인003"
    assert re.fullmatch(r"010-\d{4}-\d{4}", d["phone"])
    assert len(allc) == len(REC)


def test_v1_emits_deprecation_warning():
    from crmkit.client_v1 import CRMClient
    with pytest.warns(DeprecationWarning):
        CRMClient(backend())


def test_cli_report_runs(capsys):
    from app import cli
    cli.main(["report"])
    assert capsys.readouterr().out.split() == ["2026-07", "2", "2026-08", "1"]
