"""Docker environment for one SWE-bench Verified instance (rows of instances.jsonl).

prepare(inst, run_dir) -> (work_dir, prompt)
    run_dir/work/repo   host copy of the image's /testbed (the agent edits it)
    run_dir/work/envrun runs its arguments in the agent container, cwd /testbed, conda env on;
                        the container bind-mounts run_dir/work/repo at /testbed
grade(inst, run_dir) -> dict
    git diff of the host repo (minus files the eval script's test patch touches) is
    applied in a FRESH container, the instance's eval script runs, the log is parsed
    with swebench's parser for the repo, and SWE-bench's rule decides resolution
    (every FAIL_TO_PASS and every PASS_TO_PASS test passes).
teardown(run_dir)
    removes every container labelled with this run_dir.

Requires: docker, git on the host, `pip install swebench` (log parsers + grading).
"""
import hashlib
import json
import os
import re
import shlex
import subprocess
import tempfile
import time
from pathlib import Path

LABEL = "wrxp.swe.run"
ACTIVATE = "source /opt/miniconda3/bin/activate && conda activate testbed"
EVAL_TIMEOUT = 1800
START, END = ">>>>> Start Test Output", ">>>>> End Test Output"
# The host's egress proxy intercepts TLS; give pip inside containers its CA (tests are unaffected).
PROXY_CA = Path("/root/.ccr/ca-bundle.crt")


def _sh(args, **kw):
    kw.setdefault("check", True)
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    return subprocess.run(args, **kw)


def _tag(run_dir: Path) -> str:
    return hashlib.sha1(str(Path(run_dir).resolve()).encode()).hexdigest()[:10]


def _name(inst, run_dir, role):
    short = re.sub(r"[^a-zA-Z0-9]+", "-", inst["instance_id"]).strip("-")[:40]
    return f"swe-{short}-{_tag(run_dir)}-{role}"


def _start(inst, run_dir, role, mount: Path = None) -> str:
    name = _name(inst, run_dir, role)
    _sh(["docker", "rm", "-f", name], check=False)
    cmd = ["docker", "run", "-d", "--name", name, "--label", f"{LABEL}={Path(run_dir).resolve()}"]
    if mount:
        cmd += ["-v", f"{mount}:/testbed"]
    if PROXY_CA.exists():
        cmd += ["-v", f"{PROXY_CA}:/usr/local/share/proxy-ca.crt:ro", "-e", "PIP_CERT=/usr/local/share/proxy-ca.crt"]
    _sh(cmd + [inst["image"], "sleep", "infinity"])
    _sh(["docker", "exec", name, "git", "config", "--global", "--add", "safe.directory", "/testbed"])
    return name


def env_exports(inst) -> str:
    """`export X=Y` lines the eval script sets before running tests (e.g. django's LANG)."""
    lines = [l for l in inst["eval_script"].splitlines() if l.startswith("export ")]
    return "".join(l + "\n" for l in dict.fromkeys(lines))


def test_files(inst) -> list:
    """Files the eval script resets or patches: an agent edit to them would be discarded."""
    s = inst["eval_script"]
    files = set(re.findall(r"^diff --git a/(\S+) b/", s, re.M))
    files |= set(re.findall(r"^\+\+\+ b/(\S+)", s, re.M))
    for line in s.splitlines():
        if line.startswith("git checkout "):
            files |= set(line.split()[3:])
    return sorted(files)


PROMPT = """Resolve the following GitHub issue in the repository.

The repository is checked out in `repo/` (relative to your working directory). Edit the files there.

The project's environment (Python version, dependencies, installed package) lives in a container. \
Run commands in it with `./envrun <command>`: it runs the command inside the project root (the same \
directory as `repo/`, so paths are relative to `repo/`) with the project's environment activated, \
e.g. `./envrun python -m pytest tests/test_something.py -x -q` or `./envrun python reproduce.py`. \
Files you edit under `repo/` are immediately visible to `./envrun`.

Resolve the issue by changing the source code. Do not modify existing tests. When you are done, \
leave your changes in the working tree of `repo/` (no need to commit).

<issue>
{issue}
</issue>
"""


def prepare(inst: dict, run_dir) -> tuple:
    run_dir = Path(run_dir).resolve()
    work = run_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    repo = work / "repo"
    if repo.exists():
        _sh(["rm", "-rf", str(repo)])
    # 1) throwaway container to copy /testbed out (a created container is enough for docker cp)
    tmp = _name(inst, run_dir, "copy")
    _sh(["docker", "rm", "-f", tmp], check=False)
    _sh(["docker", "create", "--name", tmp, "--label", f"{LABEL}={run_dir}", inst["image"], "sleep", "infinity"])
    try:
        _sh(["docker", "cp", f"{tmp}:/testbed", str(repo)])
    finally:
        _sh(["docker", "rm", "-f", tmp], check=False)
    _sh(["git", "config", "--global", "--add", "safe.directory", str(repo)], check=False)
    # remember the base commit: the agent may commit, the diff is always taken against this
    (run_dir / "base_commit").write_text(_sh(["git", "-C", str(repo), "rev-parse", "HEAD"]).stdout.strip())
    # 2) agent container with the host copy mounted at /testbed
    name = _start(inst, run_dir, "agent", mount=repo)
    envrun = work / "envrun"
    envrun.write_text(
        "#!/bin/bash\n"
        "# Run a command inside the project's container, in /testbed (= ./repo), with its conda env.\n"
        f"exec docker exec -i -w /testbed {name} bash -c "
        + shlex.quote('args=("$@"); set --; ' + env_exports(inst).replace("\n", "; ")
                      + ACTIVATE + ' && exec "${args[@]}"')
        + ' envrun "$@"\n'
    )
    envrun.chmod(0o755)
    return work, PROMPT.format(issue=inst["problem_statement"].strip())


def source_diff(inst, repo: Path, base: str = "HEAD") -> str:
    """Diff of the agent's working tree vs base (untracked files included), minus test files."""
    with tempfile.TemporaryDirectory() as td:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(td) / "index")}
        g = ["git", "-C", str(repo)]
        _sh(g + ["read-tree", base], env=env)
        _sh(g + ["add", "-A", "."], env=env)
        excl = [f":(exclude){f}" for f in test_files(inst)]
        excl += [":(exclude,glob)**/__pycache__/**", ":(exclude,glob)**/*.pyc", ":(exclude,glob)**/.pytest_cache/**"]
        return _sh(g + ["diff", "--cached", "--binary", base, "--", "."] + excl, env=env).stdout


def _count_lines(patch: str) -> int:
    return sum(1 for l in patch.splitlines()
               if (l.startswith("+") and not l.startswith("+++")) or (l.startswith("-") and not l.startswith("---")))


def parse_log(inst, log: str) -> dict:
    from swebench.harness.log_parsers.python import MAP_REPO_TO_PARSER_PY
    parser = MAP_REPO_TO_PARSER_PY[inst["repo"]]
    if START in log and END in log:
        sliced = log.split(START)[1].split(END)[0]
        return parser(sliced, None) or parser(log, None)
    return {}


def grade(inst: dict, run_dir) -> dict:
    from swebench.harness.grading import get_eval_tests_report, get_resolution_status
    from swebench.harness.constants import ResolvedStatus
    run_dir = Path(run_dir).resolve()
    bc = run_dir / "base_commit"
    patch = source_diff(inst, run_dir / "work" / "repo", bc.read_text().strip() if bc.exists() else "HEAD")
    gdir = run_dir / "grade"
    gdir.mkdir(exist_ok=True)
    (gdir / "model.patch").write_text(patch)
    (gdir / "eval.sh").write_text(inst["eval_script"])
    res = {"resolved": False, "f2p_passed": 0, "f2p_total": len(inst["FAIL_TO_PASS"]),
           "p2p_failed": None, "p2p_total": len(set(inst["PASS_TO_PASS"]) - set(inst.get("P2P_ENV_EXCLUDED", []))),
           "patch_lines": _count_lines(patch), "patch_applied": True, "error": None,
           "f2p_failures": list(inst["FAIL_TO_PASS"]), "p2p_failures": None}
    res["p2p_failed"] = res["p2p_total"]
    t0 = time.time()
    name = _start(inst, run_dir, "grade")
    try:
        _sh(["docker", "cp", str(gdir / "eval.sh"), f"{name}:/eval.sh"])
        if patch.strip():
            _sh(["docker", "cp", str(gdir / "model.patch"), f"{name}:/tmp/model.patch"])
            ap = None
            for cmd in ("git apply --verbose /tmp/model.patch",
                        "git apply --verbose --reject /tmp/model.patch",
                        "patch --batch --fuzz=5 -p1 -i /tmp/model.patch"):
                ap = _sh(["docker", "exec", "-w", "/testbed", name, "bash", "-c", cmd], check=False)
                if ap.returncode == 0:
                    break
            (gdir / "apply.log").write_text(ap.stdout + ap.stderr)
            if ap.returncode != 0:
                res.update(patch_applied=False, error="patch did not apply")
                return res
        try:
            ev = _sh(["docker", "exec", name, "bash", "/eval.sh"], check=False, timeout=EVAL_TIMEOUT)
            log = ev.stdout + "\n" + ev.stderr
        except subprocess.TimeoutExpired as e:
            log = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            res["error"] = "eval timeout"
        (gdir / "test_output.txt").write_text(log)
        status = parse_log(inst, log)
        if not status:
            res["error"] = res["error"] or "no test results parsed"
            return res
        # P2P tests that fail in this sandbox even with an officially resolving patch (e.g. they
        # need outbound network); listed per instance by validate.py --update
        skip = set(inst.get("P2P_ENV_EXCLUDED", []))
        gold = {"FAIL_TO_PASS": inst["FAIL_TO_PASS"], "PASS_TO_PASS": [t for t in inst["PASS_TO_PASS"] if t not in skip]}
        rep = get_eval_tests_report(status, gold)
        (gdir / "report.json").write_text(json.dumps(rep, indent=1))
        res.update(f2p_passed=len(rep["FAIL_TO_PASS"]["success"]),
                   p2p_failed=len(rep["PASS_TO_PASS"]["failure"]),
                   f2p_failures=rep["FAIL_TO_PASS"]["failure"], p2p_failures=rep["PASS_TO_PASS"]["failure"],
                   resolved=get_resolution_status(rep) == ResolvedStatus.FULL.value)
        return res
    finally:
        res["eval_sec"] = round(time.time() - t0, 1)
        _sh(["docker", "rm", "-f", name], check=False)
        (gdir / "grade.json").write_text(json.dumps(res, indent=1))


def teardown(run_dir) -> None:
    run_dir = Path(run_dir).resolve()
    ids = _sh(["docker", "ps", "-aq", "--filter", f"label={LABEL}={run_dir}"], check=False).stdout.split()
    if ids:
        _sh(["docker", "rm", "-f", *ids], check=False)
