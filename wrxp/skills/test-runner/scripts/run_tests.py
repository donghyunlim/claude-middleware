#!/usr/bin/env python3
"""Run one existing test command and return bounded, source-backed evidence."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


LOG_PREVIEW_BYTES = 8192
SOURCE_PREVIEW_BYTES = 24000


def digest(path):
    try:
        with path.open("rb") as stream:
            result = hashlib.sha256()
            for chunk in iter(lambda: stream.read(65536), b""):
                result.update(chunk)
            return result.hexdigest()
    except OSError:
        return None


def git_state(cwd):
    def read(*args):
        try:
            result = subprocess.run(
                ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=3,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    head = read("rev-parse", "HEAD")
    status = read("status", "--porcelain", "--untracked-files=normal") if head else None
    return {"head": head, "dirty": bool(status) if status is not None else None}


def sources_before(cwd, names):
    records = []
    remaining = SOURCE_PREVIEW_BYTES
    for name in dict.fromkeys(names):
        path = (cwd / name).resolve()
        if not path.is_relative_to(cwd) or not path.is_file():
            raise ValueError(f"Source must be a file inside --cwd: {name}")
        preview = bytearray()
        checksum = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(65536), b""):
                checksum.update(chunk)
                size += len(chunk)
                preview.extend(chunk[:max(0, remaining - len(preview))])
        numbered = "\n".join(f"{i}: {line}" for i, line in enumerate(
            preview.decode("utf-8", errors="replace").splitlines(), 1)).encode("utf-8")
        text = numbered[:remaining].decode("utf-8", errors="ignore")
        truncated = size > len(preview) or len(numbered) > remaining
        remaining -= len(text.encode("utf-8"))
        records.append({
            "path": str(path), "sha256_before": checksum.hexdigest(),
            "text": text, "preview_truncated": truncated,
        })
    return records


def log_record(path):
    size = path.stat().st_size
    with path.open("rb") as stream:
        if size > LOG_PREVIEW_BYTES:
            stream.seek(-LOG_PREVIEW_BYTES, os.SEEK_END)
        preview = stream.read(LOG_PREVIEW_BYTES).decode("utf-8", errors="replace")
    return {"path": str(path), "bytes": size, "sha256": digest(path),
            "preview": preview, "preview_truncated": size > LOG_PREVIEW_BYTES,
            "preview_region": "tail"}


def freeze_log(stream, destination):
    """Snapshot bytes already captured; descendant processes cannot mutate it."""
    remaining = os.fstat(stream.fileno()).st_size
    stream.seek(0)
    with destination.open("wb") as target:
        while remaining:
            chunk = stream.read(min(remaining, 65536))
            if not chunk:
                break
            target.write(chunk)
            remaining -= len(chunk)


def stop(process):
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        process.kill()
    process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, help="Existing parent for a unique evidence directory")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--source", action="append", default=[], help="Explicit source file relative to cwd")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cwd = args.cwd.resolve()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not cwd.is_dir():
        parser.error("provide an existing --cwd and a command after --")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    if args.output_dir and not args.output_dir.is_dir():
        parser.error("--output-dir must already exist")
    try:
        sources = sources_before(cwd, args.source)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    before = git_state(cwd)
    directory = Path(tempfile.mkdtemp(prefix="wrxp-test-", dir=args.output_dir)).resolve()
    stdout, stderr = directory / "stdout.log", directory / "stderr.log"
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    status, exit_code, error_text = "not_started", None, None
    with tempfile.TemporaryFile(dir=directory) as out, tempfile.TemporaryFile(dir=directory) as err:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err,
                                       stdin=subprocess.DEVNULL, start_new_session=os.name == "posix")
            try:
                exit_code = process.wait(timeout=args.timeout)
                status = "completed"
            except subprocess.TimeoutExpired:
                status = "timed_out"
                stop(process)
                exit_code = process.returncode
        except OSError as error:
            error_text = f"{type(error).__name__}: {error}"
        freeze_log(out, stdout)
        freeze_log(err, stderr)
    elapsed = time.monotonic() - started
    for source in sources:
        source["sha256_after"] = digest(Path(source["path"]))
        source["changed_during_run"] = source["sha256_before"] != source["sha256_after"]
    record = {
        "schema_version": 1, "record_path": str(directory / "result.json"),
        "cwd": str(cwd), "command": command, "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": elapsed, "timeout_seconds": args.timeout,
        "execution_status": status, "command_exit_code": exit_code,
        "start_error": error_text, "git_before": before, "git_after": git_state(cwd),
        "sources": sources, "stdout": log_record(stdout), "stderr": log_record(stderr),
        "limits": {"log_preview_bytes_per_stream": LOG_PREVIEW_BYTES,
                   "source_preview_bytes_total": SOURCE_PREVIEW_BYTES,
                   "log_scope": "snapshot at command exit or timeout; not later descendant output",
                   "snapshot_scope": "explicit sources and git metadata only; not a cache key"},
    }
    rendered = json.dumps(record, ensure_ascii=False, indent=2)
    Path(record["record_path"]).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if status == "timed_out":
        return 124
    if status == "not_started":
        return 127
    return exit_code if exit_code >= 0 else 128 - exit_code


if __name__ == "__main__":
    raise SystemExit(main())
