import ast
import importlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HID = Path(__file__).resolve().parent
SETS = ["mixed", "many_products", "many_customers", "many_rates"]


def new_build():
    from salesreport.report import build_report
    return build_report


def orig_build():
    sys.path.insert(0, str(HID / "baseline"))
    try:
        return importlib.import_module("salesreport_orig.report").build_report
    finally:
        sys.path.remove(str(HID / "baseline"))


def golden(name):
    return (HID / "golden" / f"{name}.txt").read_text(encoding="utf-8")


def test_output_identical_to_golden():
    b = new_build()
    assert b(str(ROOT / "data")) == (ROOT / "expected" / "report.txt").read_text(encoding="utf-8")
    for n in SETS:
        assert b(str(HID / "datasets" / n)) == golden(n), n


def test_cli_writes_identical_bytes(tmp_path):
    out = tmp_path / "r.txt"
    p = subprocess.run([sys.executable, "-m", "salesreport.cli", str(HID / "datasets" / "mixed"), str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    assert out.read_bytes() == (HID / "golden" / "mixed.txt").read_bytes()


def test_no_third_party_imports():
    allowed = set(sys.stdlib_module_names) | {"salesreport"}
    bad = []
    for f in (ROOT / "salesreport").rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module]
            else:
                continue
            bad += [(f.name, m) for m in mods if m.split(".")[0] not in allowed]
    assert not bad, bad


def test_reads_fresh_data_each_call(tmp_path):
    b = new_build()
    d = tmp_path / "data"
    shutil.copytree(ROOT / "data", d)
    b(str(ROOT / "data"))
    b(str(d))
    lines = (d / "products.csv").read_text(encoding="utf-8").splitlines()
    cols = lines[1].split(",")
    cols[3] = str(float(cols[3]) * 7 + 1)
    lines[1] = ",".join(cols)
    (d / "products.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with open(d / "customers.csv", "a", encoding="utf-8") as f:
        f.write("C99999,신규고객,세종,VIP\n")
    with open(d / "order_lines.csv", "a", encoding="utf-8") as f:
        f.write(f"O999999,2026-09-30,C99999,{cols[0]},3\n")
    want = orig_build()(str(d))
    assert b(str(d)) == want
    assert want != (ROOT / "expected" / "report.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", SETS)
def test_at_least_5x_faster(name):
    data = str(HID / "datasets" / name)
    nb, ob = new_build(), orig_build()
    nb(data)  # warm-up
    best = float("inf")
    for _ in range(3):
        t0 = time.perf_counter()
        nb(data)
        best = min(best, time.perf_counter() - t0)
    t0 = time.perf_counter()
    ob(data)
    orig = time.perf_counter() - t0
    assert best * 5 <= orig, f"{name}: new {best:.3f}s vs original {orig:.3f}s"
