import datetime as dt
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = set(['C0006', 'C0009', 'C0013', 'C0014', 'C0015', 'C0016', 'C0025', 'C0029', 'C0030', 'C0033', 'C0042', 'C0043', 'C0045', 'C0046', 'C0048', 'C0053', 'C0054', 'C0061', 'C0062', 'C0070', 'C0073', 'C0074', 'C0075', 'C0081', 'C0083', 'C0085', 'C0088', 'C0090', 'C0091', 'C0095', 'C0097', 'C0098', 'C0104', 'C0107', 'C0110', 'C0113', 'C0115', 'C0117', 'C0118', 'C0121', 'C0124', 'C0130', 'C0131', 'C0134', 'C0140', 'C0141', 'C0145', 'C0150', 'C0158', 'C0162', 'C0163', 'C0165', 'C0174', 'C0175', 'C0179', 'C0183', 'C0184', 'C0185', 'C0190', 'C0191'])
NEVER_PURCHASED = set(['C0001', 'C0002', 'C0003', 'C0008', 'C0020', 'C0031', 'C0034', 'C0040', 'C0067', 'C0069', 'C0071', 'C0106', 'C0112', 'C0122', 'C0123', 'C0128', 'C0132', 'C0142', 'C0147', 'C0148', 'C0151', 'C0152', 'C0153', 'C0156', 'C0160', 'C0164', 'C0167', 'C0169', 'C0170', 'C0172', 'C0177', 'C0180', 'C0192', 'C0193', 'C0194', 'C0197'])
OPT_OUT = set(['C0004', 'C0007', 'C0022', 'C0023', 'C0024', 'C0027', 'C0028', 'C0031', 'C0038', 'C0039', 'C0041', 'C0044', 'C0056', 'C0057', 'C0058', 'C0059', 'C0060', 'C0063', 'C0064', 'C0066', 'C0068', 'C0076', 'C0077', 'C0079', 'C0087', 'C0094', 'C0096', 'C0101', 'C0102', 'C0103', 'C0106', 'C0119', 'C0120', 'C0122', 'C0125', 'C0126', 'C0127', 'C0132', 'C0133', 'C0135', 'C0136', 'C0137', 'C0138', 'C0139', 'C0143', 'C0151', 'C0154', 'C0155', 'C0157', 'C0159', 'C0160', 'C0166', 'C0176', 'C0177', 'C0178', 'C0181', 'C0187', 'C0194', 'C0195', 'C0196', 'C0198', 'C0200'])
FOOTER = "본 메일은 수신 동의하신 고객님께 발송되었습니다. 수신을 원하지 않으시면 [수신거부]를 눌러 주세요."


@pytest.fixture(scope="module")
def plan():
    return json.loads((ROOT / "campaign.json").read_text(encoding="utf-8"))


def norm(s):
    return re.sub(r"\s+", "", s)


def test_target_exact_segment(plan):
    # opt-in, purchased before, last order on/before 2026-08-03 (90+ days before 2026-11-01)
    assert set(plan["target_customer_ids"]) == EXPECTED


def test_target_opt_in_only(plan):
    assert not set(plan["target_customer_ids"]) & OPT_OUT


def test_target_excludes_never_purchased(plan):
    assert not set(plan["target_customer_ids"]) & NEVER_PURCHASED


def test_send_at_tuesday_10_kst(plan):
    t = dt.datetime.fromisoformat(plan["send_at"].replace("Z", "+00:00"))
    assert t.utcoffset() == dt.timedelta(hours=9)
    assert t == dt.datetime(2026, 11, 17, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))


def test_two_distinct_subjects(plan):
    s = plan["subjects"]
    assert len(s) == 2 and s[0].strip() != s[1].strip()


def test_subjects_ad_prefix(plan):
    assert all(x.startswith("(광고)") for x in plan["subjects"])


def test_subjects_max_30_chars(plan):
    assert plan["subjects"] and all(len(x) <= 30 for x in plan["subjects"])


def test_coupon_reactivation_code(plan):
    assert plan["coupon_code"] == "COMEBACK15"


def test_holdout_20pct(plan):
    assert float(plan["holdout_pct"]) == 20


def test_footer_unsubscribe_text_verbatim(plan):
    assert norm(FOOTER) in norm(plan["footer"])
