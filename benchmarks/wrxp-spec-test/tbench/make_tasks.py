#!/usr/bin/env python3
"""Build tasks.jsonl + tasks/<id>/{tests,solution} from a terminal-bench-2 clone.

Usage: python3 make_tasks.py /path/to/terminal-bench-2 [id,id,...]
"""
import json
import shutil
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = [
    "git-leak-recovery", "polyglot-c-py", "sqlite-db-truncate", "db-wal-recovery",
    "multi-source-data-merger", "sanitize-git-repo", "query-optimize", "constraints-scheduling",
]


def main():
    src = Path(sys.argv[1])
    ids = sys.argv[2].split(",") if len(sys.argv) > 2 else DEFAULT
    rows = []
    for tid in ids:
        d = src / tid
        t = tomllib.loads((d / "task.toml").read_text())
        m, e = t["metadata"], t["environment"]
        dst = HERE / "tasks" / tid
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(d / "tests", dst / "tests")
        shutil.copytree(d / "solution", dst / "solution")
        rows.append({
            "id": tid,
            "category": m.get("category"),
            "difficulty": m.get("difficulty"),
            "tags": m.get("tags", []),
            "instruction": (d / "instruction.md").read_text().strip(),
            # environment: prebuilt image named in task.toml (the Dockerfile in the TB2 repo builds the same thing)
            "image": e["docker_image"],
            "cpus": e.get("cpus", 1),
            "memory_mb": e.get("memory_mb", 2048),
            "allow_internet": e.get("allow_internet", True),
            # tests: TB/harbor copies tests/ to /tests and runs `bash /tests/test.sh` in the image WORKDIR;
            # reward in /logs/verifier/reward.txt, per-test results in /logs/verifier/ctrf.json
            "tests_dir": f"tasks/{tid}/tests",
            "test_cmd": "bash /tests/test.sh",
            "solution_dir": f"tasks/{tid}/solution",
            "solution_cmd": "bash /solution/solve.sh",
            "agent_timeout_sec": t["agent"]["timeout_sec"],
            "verifier_timeout_sec": t["verifier"]["timeout_sec"],
            "build_timeout_sec": e.get("build_timeout_sec", 600),
            "env": t.get("verifier", {}).get("env", {}),
        })
    with open(HERE / "tasks.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} tasks")


if __name__ == "__main__":
    main()
