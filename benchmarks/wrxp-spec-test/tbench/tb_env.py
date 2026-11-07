"""Terminal-Bench 2 environment adapter: the agent runs on the host, the task runs in a container.

prepare(task, run_dir) -> (work_dir, prompt)   pull image, start container, write work/envrun + work/envcp
grade(task, run_dir)   -> {"resolved", "passed", "total", ...}   run the task's tests/test.sh like TB/harbor
teardown(run_dir)                              remove the container

Network: task containers run with --network none (this sandbox's egress is a host-only CONNECT proxy,
and Debian mirrors / astral.sh are blocked anyway). test.sh is run unchanged; its internet steps
(apt-get install curl, curl astral.sh/uv | sh, uvx downloading python + wheels) are served from an
offline verifier kit copied in at grade time only (.cache/kit: uv 0.9.5, CPython 3.13 standalone,
wheelhouse), bind-mounted read-only at /opt/tbkit; uv itself is copied to ~/.local/bin at grade time only. Build the kit with `python3 tb_env.py kit`.
"""
import hashlib
import json
import os
import shlex
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE / ".cache" / "kit"
KIT_WHEELS = ["pytest==8.4.1", "pytest-json-ctrf==0.3.5", "gitpython==3.1.44", "pandas==2.3.3", "pyarrow==22.0.0"]
UV_URL = "https://github.com/astral-sh/uv/releases/download/0.9.5/uv-x86_64-unknown-linux-musl.tar.gz"
_pull_lock = threading.Lock()

NOTE = """

---
Environment note: the task environment is a Linux Docker container (working directory {wd}). You cannot reach its filesystem directly; the current local directory is NOT part of it. Do all the work inside the container by running shell commands through `./envrun '<shell command>'` (each call is a fresh non-interactive `bash -lc` in {wd} as root, so `cd` and exported variables do not persist between calls; stdin is forwarded, e.g. `./envrun 'cat > {wd}/x.py' < x.py`). Copy files with `./envcp SRC DST`, prefixing container paths with ':' (e.g. `./envcp :{wd}/out.txt ./out.txt`, `./envcp ./fix.py :{wd}/fix.py`). Start long-running processes detached with output redirected (`./envrun 'nohup cmd > /tmp/cmd.log 2>&1 &'`), otherwise envrun will not return. The container has no network access."""


def load_tasks(path=HERE / "tasks.jsonl"):
    return {t["id"]: t for t in map(json.loads, Path(path).read_text().splitlines())}


def _sh(args, timeout=None, check=True, **kw):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=check, **kw)


def ensure_image(task):
    img = task["image"]
    with _pull_lock:
        if _sh(["docker", "image", "inspect", img], check=False).returncode != 0:
            _sh(["docker", "pull", "-q", img], timeout=task.get("build_timeout_sec", 600))
    return img


def _state(run_dir):
    return json.loads((Path(run_dir) / "env.json").read_text())


def prepare(task, run_dir):
    run_dir = Path(run_dir).resolve()
    work = run_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    img = ensure_image(task)
    if not (KIT / "bin" / "uv").exists():
        build_kit()
    wd = _sh(["docker", "image", "inspect", "-f", "{{.Config.WorkingDir}}", img]).stdout.strip() or "/"
    tag = hashlib.sha1(str(run_dir).encode()).hexdigest()[:8]
    name = f"tb2-{task['id']}-{tag}-{uuid.uuid4().hex[:6]}"
    if (run_dir / "env.json").exists():  # stale container from an interrupted run
        _sh(["docker", "rm", "-f", _state(run_dir)["name"]], check=False)
    _sh(["docker", "run", "-d", "--name", name, "--network", "none", "--hostname", "tb2",
         "--cpus", str(task.get("cpus", 1)), "--memory", f"{task.get('memory_mb', 2048)}m",
         "--label", "tb2-harness=1", "-v", f"{KIT}:/opt/tbkit:ro", "--entrypoint", "sh", img, "-c", "sleep infinity"], timeout=120)
    _sh(["docker", "exec", name, "mkdir", "-p", "/logs/agent", "/logs/verifier"])
    (run_dir / "env.json").write_text(json.dumps({"name": name, "workdir": wd, "image": img, "task": task["id"]}))
    envrun = work / "envrun"
    envrun.write_text(f"""#!/bin/bash
# Run a shell command inside the task container ({task['id']}).
if [ $# -eq 0 ]; then echo "usage: ./envrun '<shell command>'" >&2; exit 2; fi
exec docker exec -i -w {shlex.quote(wd)} {name} bash -lc "$*"
""")
    envcp = work / "envcp"
    envcp.write_text(f"""#!/bin/bash
# Copy files between here and the task container; container paths start with ':'.
if [ $# -ne 2 ]; then echo "usage: ./envcp SRC DST   (container paths start with ':', e.g. ./envcp :{wd}/f ./f)" >&2; exit 2; fi
conv() {{ case "$1" in :/*) echo "{name}:${{1#:}}";; :*) echo "{name}:{wd}/${{1#:}}";; *) echo "$1";; esac; }}
exec docker cp "$(conv "$1")" "$(conv "$2")"
""")
    envrun.chmod(0o755)
    envcp.chmod(0o755)
    return work, task["instruction"] + NOTE.format(wd=wd)


def _exec(name, cmd, timeout=None, env=None, input=None):
    args = ["docker", "exec", "-i"]
    for k, v in (env or {}).items():
        args += ["-e", f"{k}={v}"]
    return subprocess.run(args + [name, "bash", "-c", cmd], capture_output=True, text=True,
                          timeout=timeout, input=input)


def install_kit(name):
    """Stand-in for test.sh's blocked `curl astral.sh/uv | sh`: uv at ~/.local/bin + its env file.
    Python + wheels come from the read-only kit mount at /opt/tbkit (bind-mounted at prepare)."""
    _exec(name, "mkdir -p /root/.local/bin && cp /opt/tbkit/bin/uv /opt/tbkit/bin/uvx /root/.local/bin/ && "
                "printf '%s\\n' 'case \":${PATH}:\" in *:\"$HOME/.local/bin\":*) ;; *) export PATH=\"$HOME/.local/bin:$PATH\" ;; esac' "
                "> /root/.local/bin/env")


KIT_ENV = {
    "UV_PYTHON_INSTALL_DIR": "/opt/tbkit/python", "UV_PYTHON_DOWNLOADS": "never",
    "UV_OFFLINE": "1", "UV_FIND_LINKS": "/opt/tbkit/wheels",
    "PIP_NO_INDEX": "1", "PIP_FIND_LINKS": "/opt/tbkit/wheels",
}


def grade(task, run_dir):
    run_dir = Path(run_dir).resolve()
    st = _state(run_dir)
    name = st["name"]
    t0 = time.time()
    install_kit(name)
    _exec(name, "rm -rf /tests && mkdir -p /logs/verifier && rm -f /logs/verifier/reward.txt /logs/verifier/ctrf.json")
    _sh(["docker", "cp", str(HERE / task["tests_dir"]), f"{name}:/tests"])
    env = dict(KIT_ENV, **(task.get("env") or {}))
    cmd = f"cd {shlex.quote(st['workdir'])} && {task['test_cmd']} > /logs/verifier/test-stdout.txt 2>&1"
    try:
        _exec(name, cmd, timeout=min(task.get("verifier_timeout_sec", 900), 1800), env=env)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
    test_sec = time.time() - t0
    log = _exec(name, "cat /logs/verifier/test-stdout.txt").stdout
    (run_dir / "grade.log").write_text(log)
    reward_s = _exec(name, "cat /logs/verifier/reward.txt").stdout.strip()
    ctrf_s = _exec(name, "cat /logs/verifier/ctrf.json").stdout
    try:
        reward = float(reward_s)
    except ValueError:
        reward = 0.0
    passed = total = 0
    try:
        summ = json.loads(ctrf_s)["results"]["summary"]
        passed, total = summ.get("passed", 0), summ.get("tests", 0)
        (run_dir / "ctrf.json").write_text(ctrf_s)
    except (ValueError, KeyError):
        pass
    res = {"resolved": reward >= 1.0 and not timed_out, "passed": passed, "total": total,
           "reward": reward, "timed_out": timed_out, "test_sec": round(test_sec, 1)}
    (run_dir / "grade.json").write_text(json.dumps(res, indent=1))
    return res


def teardown(run_dir):
    p = Path(run_dir).resolve() / "env.json"
    if p.exists():
        _sh(["docker", "rm", "-f", json.loads(p.read_text())["name"]], check=False)


def build_kit():
    """Download the offline verifier kit on the host (needs GitHub release + PyPI access)."""
    import tarfile
    import tempfile
    (KIT / "bin").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tgz = Path(td) / "uv.tgz"
        _sh(["curl", "-sSLf", "-o", str(tgz), UV_URL], timeout=300)
        with tarfile.open(tgz) as tf:
            for m in tf.getmembers():
                if Path(m.name).name in ("uv", "uvx") and m.isfile():
                    (KIT / "bin" / Path(m.name).name).write_bytes(tf.extractfile(m).read())
                    (KIT / "bin" / Path(m.name).name).chmod(0o755)
    _sh([str(KIT / "bin" / "uv"), "python", "install", "3.13"], timeout=600,
        env=dict(os.environ, UV_PYTHON_INSTALL_DIR=str(KIT / "python")))
    _sh([sys.executable, "-m", "pip", "download", "-q", "--dest", str(KIT / "wheels"), "--only-binary=:all:",
         "--python-version", "3.13", "--implementation", "cp", "--abi", "cp313",
         "--platform", "manylinux_2_28_x86_64", "--platform", "manylinux_2_17_x86_64",
         "--platform", "manylinux2014_x86_64", "--platform", "any"] + KIT_WHEELS, timeout=600)


if __name__ == "__main__":
    if sys.argv[1:] == ["kit"]:
        build_kit()
        print("kit ready at", KIT)
