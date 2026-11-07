import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {"customer_name", "order_id", "refund_amount", "payment_method", "refund_link", "agent_name"}
WANT = {"REFUND_STATUS", "CARD_CANCEL_DELAY", "PARTIAL_REFUND"}


@pytest.fixture(scope="module")
def macros():
    data = json.loads((ROOT / "macros.json").read_text(encoding="utf-8-sig"))
    assert isinstance(data, list)
    for m in data:
        assert isinstance(m.get("scenario"), str) and isinstance(m.get("title"), str) and isinstance(m.get("body"), str)
    return data


def by(macros, code):
    return next(m["body"] for m in macros if m["scenario"].strip() == code)


def test_three_requested_scenarios(macros):
    assert len(macros) == 3
    assert {m["scenario"].strip() for m in macros} == WANT


def test_body_length_limit(macros):
    for m in macros:
        assert len(m["body"]) <= 350, (m["scenario"], len(m["body"]))


def test_greeting(macros):
    for m in macros:
        assert m["body"].lstrip().startswith("{{customer_name}} 고객님"), m["scenario"]


def test_refund_link_token_everywhere(macros):
    for m in macros:
        assert "{{refund_link}}" in m["body"], m["scenario"]


def test_only_allowed_placeholders(macros):
    for m in macros:
        toks = set(re.findall(r"\{\{\s*([^{}]+?)\s*\}\}", m["body"]))
        assert toks <= ALLOWED, (m["scenario"], toks - ALLOWED)
        assert "refund_status_url" not in m["body"]


def test_processing_time_from_current_policy(macros):
    pat = re.compile(r"영업일\s*기준\s*3\s*[~\-–〜]\s*7\s*일")
    for code in ("REFUND_STATUS", "CARD_CANCEL_DELAY"):
        assert pat.search(by(macros, code)), code
    for m in macros:
        assert not re.search(r"2\s*[~\-–〜]\s*3\s*일", m["body"]), m["scenario"]


def test_partial_refund_amount_and_coupon(macros):
    b = by(macros, "PARTIAL_REFUND")
    assert "{{refund_amount}}" in b and "쿠폰" in b


def test_formal_style_no_haeyo(macros):
    for m in macros:
        body = re.sub(r"\{\{[^{}]*\}\}", "X", m["body"])
        sentences = [s.strip() for s in re.split(r"[.?!\n]+", body) if s.strip()]
        bad = [s for s in sentences if re.search(r"요\W*$", s)]
        assert not bad, (m["scenario"], bad)
        assert "!" not in m["body"]


def test_no_date_promise(macros):
    pats = [r"\d{1,2}\s*월\s*\d{1,2}\s*일", r"\d{4}-\d{2}-\d{2}", r"내일", r"오늘\s*(중|안|내)", r"반드시", r"보장"]
    for m in macros:
        for p in pats:
            assert not re.search(p, m["body"]), (m["scenario"], p)
