import csv
import os


def read_rows(data_dir, name):
    """data_dir/name CSV를 dict 목록으로 읽는다."""
    with open(os.path.join(data_dir, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
