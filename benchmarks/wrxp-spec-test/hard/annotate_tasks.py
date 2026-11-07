#!/usr/bin/env python3
"""Draft per-task annotations: hidden decisions vs facts discoverable in the fixture.

Writes hard/tasks/<task>/annotation.json:
  {"hidden": [{"id": "H1", "decision": "...", "correct": "..."}],
   "discoverable": [{"id": "D1", "fact": "...", "where": "<fixture file>"}]}
Drafted by an LLM from intent.md + prompt.md + fixture docs, then reviewed by hand.
Usage: python3 hard/annotate_tasks.py [--tasks a,b] [--force]
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
DOC_EXT = {".md", ".txt", ".csv", ".yaml", ".yml", ".json", ".toml"}

PROMPT = """You are building a scoring key for a benchmark task. An AI agent receives the PROMPT and the FIXTURE files.
A simulated user knows the INTENT. Split everything in the INTENT that affects the correct output into two lists:

- "hidden": decisions the agent CANNOT infer from the prompt or any fixture file (it must ask, or guess). For each give
  a short decision name and the correct answer from the intent.
- "discoverable": facts the intent relies on that ARE stated in the prompt or a fixture file (the agent should read,
  not ask). Give the fact and the file it is in.
Also add to "discoverable" any decisive fact in the fixture docs that the intent does not mention but the output depends on.
Be precise and exhaustive; 3-10 items per list is typical. Korean is fine for text.

## PROMPT
{prompt}

## INTENT (known only to the simulated user)
{intent}

## FIXTURE files (docs shown in full, data files truncated)
{fixture}

Output one JSON object only:
{{"hidden": [{{"id": "H1", "decision": "...", "correct": "..."}}], "discoverable": [{{"id": "D1", "fact": "...", "where": "..."}}]}}"""


def fixture_text(fx: Path, limit=2500):
    out = []
    for p in sorted(fx.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(fx).as_posix()
        if p.suffix in DOC_EXT or p.suffix == ".py":
            t = p.read_text(errors="replace")
            cap = limit if p.suffix in (".md", ".txt", ".yaml", ".yml", ".toml", ".py") else 600
            out.append(f"### {rel}\n{t[:cap]}{' …(truncated)' if len(t) > cap else ''}")
        else:
            out.append(f"### {rel} (binary/other)")
    return "\n\n".join(out)[:40000]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    tasks = a.tasks.split(",") if a.tasks else sorted(p.name for p in TASKS.iterdir() if (p / "intent.md").exists())
    for t in tasks:
        d = TASKS / t
        out = d / "annotation.json"
        if out.exists() and not a.force:
            continue
        text = PROMPT.format(prompt=(d / "prompt.md").read_text(), intent=(d / "intent.md").read_text(),
                             fixture=fixture_text(d / "fixture"))
        p = subprocess.run(["claude", "-p", "--tools", "", "--output-format", "json"], input=text,
                           capture_output=True, text=True, timeout=900, cwd=tempfile.gettempdir())
        res = json.loads(p.stdout)["result"]
        j = json.loads(re.search(r"\{.*\}", res, re.S).group(0))
        j["_drafted_by"] = "llm; reviewed by hand"
        out.write_text(json.dumps(j, ensure_ascii=False, indent=1))
        print(t, len(j["hidden"]), "hidden,", len(j["discoverable"]), "discoverable", flush=True)


if __name__ == "__main__":
    main()
