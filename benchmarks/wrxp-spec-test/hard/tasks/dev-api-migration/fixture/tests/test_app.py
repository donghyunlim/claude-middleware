from crmkit._backend import FakeBackend
from crmkit.sample_data import SAMPLE
from app import billing, notify, reports


def b():
    return FakeBackend(SAMPLE)


def test_invoice_header():
    assert billing.invoice_header(b(), "C001", "2026-11") == "[2026-11 청구서] 고객번호 C001 / 상호 (주)한빛상사"


def test_renewal_skips_unknown():
    msgs = notify.renewal_messages(b(), ["C002", "NOPE"])
    assert len(msgs) == 1 and msgs[0].startswith("누리푸드 주식회사 담당자님")


def test_monthly_signups():
    assert reports.monthly_signups(b()) == {"2026-07": 2, "2026-08": 1}
