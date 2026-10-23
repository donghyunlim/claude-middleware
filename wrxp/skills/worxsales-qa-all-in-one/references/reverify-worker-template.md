<!-- Re-verify worker prompt. The orchestrator fills {PLACEHOLDERS} and sends it to an Opus agent, one agent per slot.
     Placeholders: RUN_ID, EXECUTOR_SKILL_DIR, QA_HOME, SLOT_DIR, PORT, BUILD, TC_IDS (comma-separated), MODEL (e.g. opus). -->
# Re-verify worker ({RUN_ID})

**Never use `pkill`, `killall` or any name/pattern kill. If a command you started hangs, kill only its PID.**

You re-check rows that a first executor judged 「문제」, or whose earlier verdict was 「문제」 and now differs. Your judgement decides what goes to developers, so be strict about what the documents actually require. Do not delegate to other agents.

## Read first
- Skill folder (<skill>): {EXECUTOR_SKILL_DIR}. Read <skill>/references/reverify.md fully and follow it; also <skill>/SKILL.md (verdict rules), references/environment.md, references/report-format.md, references/result-schema.md.
- runs/{RUN_ID}/WORKER.md: the lane's environment, write scope and 「조율자 확인」 notes apply to you too. Where it conflicts with reverify.md about the result file, reverify.md wins.

## Environment
- Repo dir: {QA_HOME}. App control: `QA_HOME={SLOT_DIR} timeout 60 node <skill>/scripts/app.mjs ...` (CDP port {PORT}, build `{BUILD}`). Use only this slot. DEV only.
- Temporary files only under `runs/{RUN_ID}/_tmp/reverify/`.

## Rows
{TC_IDS}

For each row, in order:
1. Read the scenario row (scenarios/<menu>/<screen>.json), the first result `runs/{RUN_ID}/<tc_id>.json` and its figures, and the cited sources under `sources/` (the screen document, the cited clause, the screen's CBT scope section, the role/permission document for role rows).
2. Decide what the documents actually require. Overturn a first verdict built on a requirement the documents do not state, or on a feature the CBT scope removed.
3. Reproduce it yourself in the same role and data context. Run `date +%Y-%m-%dT%H:%M:%S%z` at the real start and end.
4. Pick one conclusion: `문제 확정` (reproduced and the documents clearly differ; new numbered red-box figure), `문제 아님` (with the right final verdict), `재현 불가` (with the reason), `시나리오 문제` (the row expects more than its source; quote the source; final verdict `보류-기록`).
5. Write `runs/{RUN_ID}/_reverify/<tc_id>.json` with the fields listed in reverify.md (`reviewer_model`: `{MODEL}`). Put figures in `runs/{RUN_ID}/_reverify/` and list file names only. Do not edit the first result file; the orchestrator merges with merge_reverify.py.

## Finish
Do not publish. Leave the app on the home screen in the 영업자 role. Final report (Korean, under 120 words): per row the conclusion and final verdict, and anything that blocked reproduction.
