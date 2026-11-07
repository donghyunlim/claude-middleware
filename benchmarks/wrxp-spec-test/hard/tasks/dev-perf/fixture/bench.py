"""리포트 생성 시간 측정: python3 bench.py [DATA_DIR] [반복 횟수]"""
import sys
import time

from salesreport.report import build_report

data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
times = []
for _ in range(n):
    t0 = time.perf_counter()
    build_report(data_dir)
    times.append(time.perf_counter() - t0)
print(f"{data_dir}: best {min(times):.3f}s / runs {', '.join(f'{t:.3f}' for t in times)}")
