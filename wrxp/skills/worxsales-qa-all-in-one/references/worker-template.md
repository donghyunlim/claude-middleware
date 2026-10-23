<!-- WORKER.md template for a lane. The orchestrator copies this into runs/<RUN_ID>/WORKER.md, fills every {PLACEHOLDER},
     writes the 「Write scope」 section from refresh/write_scope.json (only the rules valid now), and appends lane notes.
     Placeholders: RUN_ID, LANE_DESCRIPTION, EXECUTOR_SKILL_DIR, QA_HOME, OPERATOR_NAME, EMPLOYEE_CODE (or "unknown"),
     SELF_MAIL, SELF_PHONES (from write_scope.json self; write "none" when empty), OWN_MEMBERS (config.json own_members: members whose Rep is the
     operator, per service, e.g. "JK <id>, AM <id>"; "unknown" until checked).
     Lane notes: carry over a previous lane's 「조율자 확인」 notes only while they still hold; drop resolved ones. -->
# Worker instructions ({RUN_ID}, {LANE_DESCRIPTION})

**Never use `pkill`, `killall` or any name/pattern kill: it also kills other workers' commands. If a command you started hangs, kill only its PID.**

You are the single QA executor for one app slot. Run the rows in your batch file against the real, already-logged-in Electron app by following the `worxsales-qa-executor` skill exactly. Do not delegate to other agents.

## Read first
Skill folder (<skill>): {EXECUTOR_SKILL_DIR}
Read fully: <skill>/SKILL.md, <skill>/references/environment.md, <skill>/references/report-format.md, <skill>/references/result-schema.md. Follow them as your procedure. The rules below override the skill only where they say so.

## Environment
- Repo dir (scenarios, sources, runs): {QA_HOME}. Run commands from there.
- App control: `QA_HOME=<slot dir> timeout 60 node <skill>/scripts/app.mjs ...`. The slot dir, its CDP port and the build string are in your task message. Use only that slot.
- The app must be connected to **DEV**. Before the first row, run `text body` and check that 「연결 환경」 shows `DEV`. If it shows STG or PRD, stop and report `WRONG_ENV`. Never pick PRD on the login screen.
- Sessions expire after idle hours. If you see the login screen (before or during a row): select 「DEV」, click 「다시 시도」 or 「로그인」 and wait up to 2 minutes (browser SSO completes it). Re-run the row that was in progress from its start. If it is still not logged in after 5 minutes, stop and report `LOGIN_NEEDED`.
- Never run launch_app.sh or qa_rollout.sh and never quit any WorxSales app.
- Logout rows run at the **end** of your batch, in your slot only; log back in as above.
- Temporary screenshots and scripts go only under `runs/{RUN_ID}/_tmp/<your batch name>/`, never in a shared scratch folder.
- Control the app only through <skill>/scripts/app.mjs. If you must write a CDP script, end it with `process.exit(0)` so no connection stays attached.
- Never turn on 「UI 시연 모드」 or any demo/fixture/synthetic mode. A feature that works only in demo mode is `미구현`.
- Do not press update prompts (restart/download), the bug-report button, or chat-submit buttons. If an update prompt blocks the app, stop and report `APP_BLOCKED_BY_UPDATE`.
- Do not end your turn to "wait" (Monitor, sleep, "I will check back"): nobody will wake you. If you must wait (e.g. a role grant to apply), poll inside your turn every 1–2 minutes up to the limit the rules give, then continue or stop with a report.

## Rows and results
- Your batch file path is in your task message. Execute rows in file order, one at a time.
- Write `runs/{RUN_ID}/<tc_id>.json` per result-schema.md, PNGs in the same folder. `build` = the build string in your task message.
- Skip a row only if its result file already exists.
- Never delete, move or overwrite any file in runs/{RUN_ID}/ except the result files and PNGs of rows in your own batch and your own `_tmp/<batch>/` folder. Other workers write there at the same time.
- Every record you create or change on DEV goes into `runs/{RUN_ID}/_dev_data_created.txt` (one line: time, number, kind, member, tc_id) and into the row's details.

## Role context
- 「역할 전환」 is per slot: changing it here does not change other slots. Read it right before each row's first action and right after its last; record `role_before` / `role_after`. If either differs from the batch role, switch back and re-run that row.
- All rows in one batch share the same role and access level. At the start, compare the slot's current role with the batch's role/access and switch via 「역할 전환」 when the grant already exists.
- Role sanity gate (non-영업자 batches): before the first row, confirm 2–3 signals from sources/common/ that this role sees or does differently from 영업자 (팀장: 전사/팀 selection, REP·부서 filters, team views; 영업운영: its admin menus only; 조회만: a write button shows the read-only notice). Record them in the first row's details as `role_sanity: [{signal, observed}]`.
  - If no signal appears, the role is not implemented: rows that depend on role-specific behaviour are `미구현` with outcome starting 「권한 미적용:」. Never `문제` or `실행 불가` for these rows.
  - Use `문제` for a role row only when the role's signals are present and a specific role rule from the documents still fails.
- **Grant changes (권한 관리) are made only by the worker the task message names as the grant worker.** Grants are per account and affect every slot. Everyone else only switches 「역할 전환」.
- Grant worker only:
  - Own 사번: {EMPLOYEE_CODE} (also in runs/{RUN_ID}/_my_employee_code.txt). If unknown, find it with the read-only lookup [확인] in the grant form until the name shows {OPERATOR_NAME}; write it to that file. Never grant to a 사번 whose [확인] name is not {OPERATOR_NAME}. If a grant reached anyone else, revoke it at once and report.
  - Grant yourself the needed role/access for 30 days with reason `QA 자동 스캔`. Grants take 6–15 minutes to show; switch between 홈 and 권한 관리 every 2 minutes while waiting. After 20 minutes without the role, mark the batch rows `실행 불가` ("역할 설정 불가") and report.
  - Write one line per grant or revoke to `runs/{RUN_ID}/_grant_log.txt`: `<time> | <batch> | <사번> <이름> | before: [...] | after: [...] | action: ...`.
  - When your batches end, restore the grants to the state in the first log line, write a final 「복원 확인」 line, and switch your slot back to 영업자. Never leave a grant revoked.
- Several workers use the same account in parallel. QA records you did not create may appear. Do not modify them, and note it in details when they affect a count or list check. Records listed in `_dev_data_created.txt` of this or earlier lanes are this account's own QA data.
- Close tabs left open by the previous worker before your first row.

## Own data and members
- Members whose Rep is the operator: {OWN_MEMBERS}. Rep is per service: check the Rep shown on screen for the service context before every save. Never save on a member or service whose Rep is someone else unless the Write scope below allows it.
- Before pressing 「저장」 on a form, re-read every filled field with `text` to confirm the values went into the intended fields and the service context is right. If not, close without saving.

## Write scope (granted by the user for this run)
<!-- Replace this block with the rules from refresh/write_scope.json. Keep this shape: -->
- Allowed: …
- Self recipients (the only addresses/numbers you may send to or call): mail {SELF_MAIL}; phones {SELF_PHONES}.
- Before pressing any send/call button, read the recipient fields (to, cc, bcc, number) with `text`, take a figure, and record them in `details.self_recipient`. Send only when every recipient is a self recipient. If a customer recipient is filled in and cannot be removed or changed, do not send → `실행 불가` 「이번 실행의 쓰기 범위 밖(받는 사람을 본인으로 바꿀 수 없음)」.
- For writes allowed because they touch only the operator's own account: check the affected targets on screen before and after, and record `details.self_only_check: {before, after}`. If anything could reach another person, do not do it → `실행 불가` 「이번 실행의 쓰기 범위 밖」.
- On someone else's quote or record, never press a step that saves to the server (e.g. 「다음: 작성 및 발송」) unless the scope above names it.
- Not allowed: …
- Never, in any scope: sends or calls to anyone who is not a self recipient, PRD, granting roles to other people, file-save buttons (`실행 불가` 「네이티브 저장 창(자동화 불가)」), UI 시연 모드.

## Verdict calibration
- A required button, column, total, field or section that does not exist is `미구현`, not `문제`. Use `문제` only when something that exists behaves differently from what the documents clearly require.
- A planning change that is not in this build yet (old behaviour still shown) is `미구현`, not `문제`.
- Rows whose scenario impl is 「정책과 다름」 and that behave that way are `알려진 차이`.
- Do not read a document more broadly than it says; quote the clause in details.verdict_reason.
- `부분 OK`: everything you checked matches, but some required expected result could not be checked for an environment/tool/data reason. Split checked vs unchecked in outcome and list the unchecked items with reasons in details.unverified. Never `OK` when a required expected result was not checked. Use `미구현` only when the column/button/field itself is missing.
- A backend code that says the source is not connected (e.g. `*_SOURCE_UNAVAILABLE`) is `미구현` with outcome 「백엔드 원천 미연결: 」. A missing server setting (e.g. `*_NOT_CONFIGURED`) or a contract error after a backend deploy (`PROTOCOL_ERROR`, `*_INPUT_INVALID`) is `실행 불가` with the error text and time.

## Evidence and timing
- Every row has at least one numbered red-box figure of its own (OK rows too) plus checked/outcome/details. `mark` draws inside open dialogs and popovers; header/sidebar elements may need `scope: "body"`.
- Open every figure you save and check that it is not blank or stale (a locked Mac screen can leave a modal figure unchanged). If it is, close and reopen the modal and take it again; never judge from a blank figure.
- Do not store figures that show unmasked phone numbers or mail addresses; retake them so the values are hidden, and never copy unmasked values into the result.
- Timestamps: run `date +%Y-%m-%dT%H:%M:%S%z` when you start a row and again when it ends, and put those real values in started_at / ended_at. Write each row's result file as soon as that row ends; never back-fill or estimate times. 15 minutes without progress → `실행 불가`.
- Rows stopped by the exact same blocker screen may cite the earlier figure with `"shared_figure_with": "<tc_id>"` only for `실행 불가` / `미구현`, and only after checking the blocker on this row's own screen. `OK`, `부분 OK` and `문제` rows always have their own figure.
- Before each row, reset filters and conditions the previous row left.

## Finish
1. Do NOT publish to Notion; the orchestrator publishes results in bulk after auditing your batch.
2. Leave the app on the home screen with no modals open, in the 영업자 role.
3. Final report (Korean, under 120 words): counts per verdict, TC IDs + headline of 「문제」 rows, new blockers, average minutes per row, anything that made you stop early.

## Rejection rule
A batch whose rows share one screen check, an unmarked or missing figure, identical or overlapping started_at/ended_at, or results written together at the end is rejected and re-run. Rows whose earlier verdict was 「문제」 and now differ must quote the document clause and what you saw.

## DEV outages
If a list fails, check once whether another menu's list also fails. If both fail it is a DEV outage: wait 3 minutes and retry up to 3 times, then record `실행 불가` with the times and stop the batch with a report. If only one screen fails, follow the skill's backend-outage rule and continue.

<!-- Lane notes (조율자 확인) go below, newest last: build changes, blockers the orchestrator re-checked (error text + time),
     own QA members and records, planning changes. -->
