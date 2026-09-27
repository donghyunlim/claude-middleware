#!/usr/bin/env python3
"""Plan, install, check, or remove WRXP's managed global routing block."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import uuid


START = "<!-- WRXP:START -->"
END = "<!-- WRXP:END -->"
INSTALLER_START = "<!-- WRXP-INSTALLER:START -->"
INSTALLER_END = "<!-- WRXP-INSTALLER:END -->"
MARKER_LINE = re.compile(r" {0,3}<!--\s*([A-Za-z][\w-]*):(START|END)\s*-->[ \t]*")
OWNED_LINE = re.compile(r"<!-- WRXP:OWNED prefix=([0-9a-f]*) bytes=([0-9]+) sha256=([0-9a-f]{64}) -->")
FENCE_OPEN = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")
SKILL_REF = re.compile(r"(?<![\w-])wrxp:([a-z][a-z0-9-]*)")


class SetupError(Exception):
    pass


def path_from(value):
    return Path(value).expanduser().absolute()


def read_target(path):
    if path.is_symlink():
        raise SetupError(f"symlink target refused: {path}")
    if not path.exists():
        return None, None
    if not path.is_file():
        raise SetupError(f"not a regular target file: {path}")
    info = path.stat()
    raw = path.read_bytes()
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SetupError(f"invalid UTF-8 target: {path}") from exc
    return raw, info


def comment_after(content, active):
    offset = 0
    while True:
        boundary = content.find("-->" if active else "<!--", offset)
        if boundary < 0:
            return active
        active = not active
        offset = boundary + (3 if not active else 4)


def scan(text):
    """Find standalone management lines outside simple Markdown fences/comments."""
    markers = []
    fence = None
    comment = False
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if fence:
            closing = re.fullmatch(r" {0,3}" + re.escape(fence[0]) +
                                   "{" + str(fence[1]) + r",}[ \t]*", content)
            if closing:
                fence = None
        else:
            opening = None if comment else FENCE_OPEN.fullmatch(content)
            if opening and (opening.group(1)[0] == "`" and "`" not in opening.group(2)
                            or opening.group(1)[0] == "~"):
                fence = (opening.group(1)[0], len(opening.group(1)))
            else:
                marker = None if comment else MARKER_LINE.fullmatch(content)
                owned = None if comment else OWNED_LINE.fullmatch(content)
                if marker:
                    markers.append(("marker", offset + len(content) - len(content.lstrip(" ")), marker))
                elif owned:
                    markers.append(("owned", offset, owned))
                comment = comment_after(content, comment)
        offset += len(line)
    return markers, fence, comment


def legacy_span(markers):
    stack = []
    wrxp = []
    ambiguous = False
    for kind, position, match in markers:
        if kind != "marker":
            continue
        name, edge = match.groups()
        if edge == "START":
            if name == "WRXP":
                wrxp.append((position, None))
            if stack or (name == "WRXP" and len(wrxp) > 1):
                ambiguous = True
            stack.append(name)
        elif not stack or stack[-1] != name:
            ambiguous = True
        else:
            stack.pop()
            if name == "WRXP":
                start, _ = wrxp[-1]
                wrxp[-1] = (start, position + len(END))
    if stack or len(wrxp) > 1:
        ambiguous = True
    if ambiguous:
        return None, True
    return (wrxp[0] if wrxp else None), False


def owned_span(text, markers):
    """Trust only a complete, hashed installer block at the end of the file."""
    for kind, position, match in reversed(markers):
        if kind != "owned":
            continue
        prefix_hex, size, digest = match.groups()
        try:
            prefix = bytes.fromhex(prefix_hex).decode("ascii")
        except (ValueError, UnicodeError):
            continue
        if prefix not in ("", "\n", "\r\n") and not re.fullmatch(
                r"(?:\r?\n)?(?:`{3,}|~{3,}|-->)(?:\r?\n)", prefix):
            continue
        start = position - len(prefix)
        record_end = position + len(match.group())
        nl = "\r\n" if text[record_end:record_end + 2] == "\r\n" else "\n"
        payload_start = record_end + len(nl)
        payload = text[payload_start:]
        if (start < 0 or text[start:position] != prefix or
                len(payload.encode("utf-8")) != int(size) or
                hashlib.sha256(payload.encode("utf-8")).hexdigest() != digest or
                not payload.startswith(INSTALLER_START + nl + START + nl) or
                not payload.endswith(nl + END + nl + INSTALLER_END + nl)):
            continue
        return start, payload_start, len(text), prefix
    return None


def newline_for(raw):
    return "\r\n" if b"\r\n" in raw else "\n"


def make_payload(body, nl):
    return (INSTALLER_START + nl + START + nl +
            body.rstrip("\r\n").replace("\r\n", "\n").replace("\n", nl) +
            nl + END + nl + INSTALLER_END + nl)


def owned_append(text, body, prefix, nl):
    payload = make_payload(body, nl)
    encoded = payload.encode("utf-8")
    record = (f"<!-- WRXP:OWNED prefix={prefix.encode('ascii').hex()} "
              f"bytes={len(encoded)} sha256={hashlib.sha256(encoded).hexdigest()} -->" + nl)
    return text + prefix + record + payload, record + payload


def transformed(raw, path, body, remove):
    text = raw.decode("utf-8") if raw is not None else ""
    markers, fence, comment = scan(text)
    owned = owned_span(text, markers)
    original_markers = [entry for entry in markers if not owned or entry[1] < owned[0]]
    span, ambiguous = legacy_span(original_markers)
    unmanaged = ambiguous or bool(owned and span)
    warnings = ["Ambiguous or unmanaged management boundaries remain; preserving original content."] if unmanaged else []
    if owned:
        start, payload_start, end, prefix = owned
        if remove:
            output = text[:start].encode("utf-8")
            return output, "removed_unmanaged" if unmanaged else "removed", unmanaged, warnings, None
        nl = newline_for(raw or b"")
        replacement, preview = owned_append("", body, prefix, nl)
        output = (text[:start] + replacement).encode("utf-8")
        return output, "unchanged" if output == raw else "updated", unmanaged, warnings, prefix + preview
    if remove:
        if span is None:
            return raw, "unmanaged" if unmanaged else "absent", unmanaged, warnings, None
        start, end = span
        if text[end:end + 2] == "\r\n":
            end += 2
        elif text[end:end + 1] == "\n":
            end += 1
        return (text[:start] + text[end:]).encode("utf-8"), "removed", False, [], None
    nl = newline_for(raw or b"")
    block = START + nl + body.rstrip("\r\n").replace("\r\n", "\n").replace("\n", nl) + nl + END
    if span is None:
        prefix = "" if not text or text.endswith(("\n", "\r")) else nl
        if fence:
            prefix += fence[0] * fence[1] + nl
        elif comment:
            prefix += "-->" + nl
        result, preview = owned_append(text, body, prefix, nl)
        return result.encode("utf-8"), "appended" if unmanaged else "added", unmanaged, warnings, prefix + preview
    start, end = span
    result = text[:start] + block + text[end:]
    output = result.encode("utf-8")
    return output, "unchanged" if output == raw else "updated", False, [], block


def bundled_skills(script):
    skills_root = script.parent.parent.parent
    return sorted(p.parent.name for p in skills_root.glob("*/SKILL.md"))


def load_body(script, inventory):
    asset = script.parent.parent / "assets/global-rules.md"
    try:
        body = asset.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SetupError(f"cannot read rules asset: {asset}") from exc
    missing = sorted(set(SKILL_REF.findall(body)) - set(inventory))
    if missing:
        raise SetupError("rules asset references missing bundled skills: " + ", ".join(missing))
    if not body.strip():
        raise SetupError("rules asset is empty")
    return body


def choose_codex_path(home):
    override = home / "AGENTS.override.md"
    raw, _ = read_target(override)
    if raw:
        return override, ["Nonempty AGENTS.override.md is the active Codex target."]
    return home / "AGENTS.md", []


def snapshot_matches(path, raw, info):
    current, current_info = read_target(path)
    if current != raw:
        return False
    if info is None:
        return current_info is None
    return (current_info is not None and
            (current_info.st_dev, current_info.st_ino, current_info.st_mtime_ns, current_info.st_mode)
            == (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_mode))


def backup_original(path, raw):
    for _ in range(10):
        backup = path.with_name(path.name + ".wrxp-backup-" + uuid.uuid4().hex)
        try:
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
            return backup
        except FileExistsError:
            continue
    raise SetupError(f"cannot allocate unique backup: {path}")


def write_atomic(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".wrxp-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--target", choices=("codex", "claude", "both"), required=True)
    cli.add_argument("--codex-home")
    cli.add_argument("--claude-home")
    action = cli.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--check", action="store_true")
    cli.add_argument("--remove", action="store_true")
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    mode = "apply" if args.apply else "check" if args.check else "plan"
    script = Path(__file__).resolve()
    inventory = bundled_skills(script)
    report = {"mode": mode, "bundled_skills": inventory, "targets": [],
              "managed_block": None}
    try:
        if args.remove and args.check:
            raise SetupError("--check --remove is unsupported")
        body = "" if args.remove else load_body(script, inventory)
        if not args.remove:
            report["managed_block"] = owned_append("", body, "", "\n")[1]
        codex_home = path_from(args.codex_home or os.environ.get("CODEX_HOME") or "~/.codex")
        claude_home = path_from(args.claude_home or os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")
        selected = ("codex", "claude") if args.target == "both" else (args.target,)
        plans = []
        for runtime in selected:
            if runtime == "codex":
                path, warnings = choose_codex_path(codex_home)
            else:
                path, warnings = claude_home / "CLAUDE.md", []
            raw, info = read_target(path)
            output, status, unmanaged, notes, preview = transformed(raw, path, body, args.remove)
            item = {"runtime": runtime, "path": str(path), "status": status,
                    "backup": None, "warnings": warnings + notes,
                    "unmanaged_rules": unmanaged}
            if preview is not None and not args.remove:
                item["planned_block"] = preview
            report["targets"].append(item)
            plans.append((path, raw, info, output, item))
        if args.apply:
            for path, raw, info, output, item in plans:
                if item["status"] in ("unchanged", "absent", "unmanaged"):
                    continue
                if not snapshot_matches(path, raw, info):
                    raise SetupError(f"target changed during setup: {path}")
                if raw is not None:
                    item["backup"] = str(backup_original(path, raw))
                if not snapshot_matches(path, raw, info):
                    raise SetupError(f"target changed during setup: {path}")
                write_atomic(path, output, stat.S_IMODE(info.st_mode) if info else 0o644)
                item["committed"] = True
        code = int(args.check and any(t["status"] != "unchanged" for t in report["targets"]))
    except (SetupError, OSError) as exc:
        report["error"] = str(exc)
        report["committed_targets"] = [t["path"] for t in report["targets"] if t.get("committed")]
        code = 2
    print(json.dumps(report, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
