<!-- WORKER.md template for a lane. The orchestrator copies this into runs/<RUN_ID>/WORKER.md, fills every {PLACEHOLDER},
     and replaces the 「Write scope」 section from refresh/write_scope.json. Placeholders: RUN_ID, LANE_DESCRIPTION,
     EXECUTOR_SKILL_DIR, QA_HOME, EMPLOYEE_CODE, OPERATOR_NAME. -->
# Full-scan worker instructions ({RUN_ID}, {LANE_DESCRIPTION})

You are the single QA executor for WorxSales. Run the rows in your batch file against the real, already-logged-in Electron app by following the `worxsales-qa-executor` skill exactly. Do not delegate to other agents.

## Read first
Skill folder (<skill>): {EXECUTOR_SKILL_DIR}
Read fully: <skill>/SKILL.md, <skill>/references/environment.md, <skill>/references/report-format.md, <skill>/references/result-schema.md. Follow them as your procedure. The rules below override the skill only where they say so.

## Environment
- Repo dir (scenarios, sources, runs): {QA_HOME}. Run commands from there.
- App control: `QA_HOME=<APP_HOME> node <skill>/scripts/app.mjs ...`. APP_HOME and its CDP port are given in your task message. Use only that app.
- The app must be connected to **DEV**. Before the first row, run `text body` and check that 「연결 환경」 shows `DEV`. If it shows STG or PRD, stop immediately and report `WRONG_ENV` (do not log out or switch it yourself).
- If you see the login screen, select the 「DEV」 environment option first, then click 「로그인」.
- Never run launch_app.sh and never quit any WorxSales app. If the app shows the login screen, click its 「로그인」 button (or 「다시 시도」) via app.mjs and wait up to 60 s; the browser SSO session completes it. If it still is not logged in, stop and report `LOGIN_NEEDED`.
- Logout rows are allowed: after logging out, select 「DEV」 on the login screen, click 「로그인」, and wait until 「역할 전환」 appears again (browser SSO completes it). Then continue.
- Put temporary screenshots and scratch files only under `runs/{RUN_ID}/_tmp/<your batch name>/`, never in a shared scratch folder (in particular never in the session scratchpad of the orchestrator; other workers write there at the same time), so files from other workers are never mistaken for yours.
- Control the app only through <skill>/scripts/app.mjs. Do not write ad-hoc CDP/playwright scripts; if you must, end them with `process.exit(0)` so no connection stays attached to the app.
- Never turn on 「UI 시연 모드」 or any demo/fixture/synthetic mode. A feature that works only in demo mode is `미구현`.

## Rows and results
- Your batch file path is in your task message. Execute rows in file order, one at a time.
- Write `runs/{RUN_ID}/<tc_id>.json` per result-schema.md, PNGs in the same folder. `build` = the build string in your task message.
- Skip a row only if its result file already exists.
- Never delete, move or overwrite any file in runs/{RUN_ID}/ except the result files and PNGs of rows in your own batch and your own _tmp/batch-<NNN>/ folder. Other executors write there at the same time.

## Role context
- Whether the selected role (「역할 전환」) is shared across apps on this account is unclear (reports conflict). So in every row: read 「역할 전환」 right before the first action and right after the last one, and record both in details as `role_before` / `role_after`. If either differs from the batch role, switch back and re-run that row. Report at once if it happens more than twice in a batch.
- Role sanity gate (non-영업자 batches): before the first row, check that the role is not just a label. Read sources/common/*.md for what this role must see or do differently from 영업자, and confirm 2–3 of those signals on screen. For 팀장: 전사/팀 selection or REP·부서 filters enabled, team views, 개입 큐. For 영업운영: only its admin menus. For 조회만: a write button shows 「지금 역할은 조회만 할 수 있습니다」. Record them in the first row's details as `role_sanity: [{signal, observed}]`.
  - If the signals do not appear (the app behaves like 영업자 although the role label changed), the role is not implemented. Then, for every row whose result depends on the role-specific behavior, the verdict is `미구현` with outcome starting 「권한 미적용:」. Never use `문제` or `실행 불가` for these rows.
  - Use `문제` for a role row only when the role's own signals are present and a specific role rule from the documents still fails.
- Your 사번 is {EMPLOYEE_CODE} (also in runs/{RUN_ID}/_my_employee_code.txt).

- All rows in one batch share the same role and access level. At the start, compare the app's current role (「역할 전환」) with the batch's role/access.
- If {EMPLOYEE_CODE} is unknown, find the operator's own 사번 with the read-only lookup ([확인]) in the 권한 관리 grant form, matching the name {OPERATOR_NAME}. Write it to runs/{RUN_ID}/_my_employee_code.txt so later workers reuse it (read that file first if it exists).
- If they differ: open 권한 관리, grant yourself the needed role with the needed access level (「수정 가능」 or 「조회만」) for 30 days with reason `QA 자동 스캔`, then switch via 「역할 전환」. Grants may need re-login or up to 15 minutes to apply; if the role does not appear, wait and retry, or log out and log in again with the 「로그인」 button. Record what you did in the first row's details.
- If the role still cannot be set after 20 minutes, mark the batch rows `실행 불가` with reason "역할 설정 불가" and report.

- Several executors use the same account in parallel on other app ports. QA records you did not create (e.g. other OP-2610-xxxx, QA- contacts) may appear. Do not modify them, and note it in details when they affect a count or list check.
- Close tabs left open by the previous worker before your first row.

- Never click 「PDF 다운로드」 or any button that downloads/saves a file: it opens a native macOS save dialog that automation cannot close and freezes the app. Mark such rows `실행 불가` with reason "네이티브 저장 창(자동화 불가)". (Opening a PDF preview inside the app is fine.)

## Write scope (granted by the user for this run)
- Allowed: creating, saving and editing test data with values prefixed `QA-`, including registering a QA record on a member another rep owns when the menu rule allows it. Record created record numbers in details.
- Allowed: role grants to yourself in 권한 관리.
- Not allowed: real sends to customers (mail/SMS/fax), phone calls, the 세그먼트 업로드 「적용하기」 button, editing or deleting data other people created. Rows needing these → `실행 불가` with reason "이번 실행의 쓰기 범위 밖".

## Verdict calibration (from the reverify pass)
- A required button, column, total, field or section that does not exist is `미구현`, not `문제`. Use `문제` only when something that exists behaves differently from what the documents clearly require.
- Rows whose scenario impl is 「정책과 다름」 and that behave that way are `알려진 차이`.
- Do not read a document more broadly than it says; quote the clause in details.verdict_reason.

- `부분 OK`: everything you checked matches, but some required expected result could not be checked for an environment/tool reason (Google not connected, no address bar, external system). Split checked vs unchecked in outcome and list the unchecked items with reasons in details.unverified. Never use `OK` when a required expected result was not checked.

## Evidence and timing
- Full evidence: every row has at least one numbered red-box figure (OK rows too) plus checked/outcome/details.
- Known tool limits: `mark` does not draw over modals (capture the modal without marks and describe it in caption); some header/sidebar elements need `scope: "body"`.
- Timestamps: run `date +%Y-%m-%dT%H:%M:%S%z` when you start a row and again when it ends, and put those real values in started_at / ended_at. Write each row's result file as soon as that row ends; never back-fill or estimate times. 15 minutes without progress → `실행 불가`.
- Each row is checked on screen and its result file is written before the next row starts. Rows judged `OK` or `문제` always get their own figure. Rows stopped by the exact same blocker screen (e.g. 「알림 원장 미연결」) may reuse that one figure; say so in details (`"shared_figure_with": "<tc_id>"`).
- When the same blocker already stopped an earlier row in this batch (e.g. 영업기회 목록 HTTP_500), confirm it once quickly on the new row and record it; do not spend long retrying.

## Finish
1. Do NOT publish to Notion; the orchestrator publishes results in bulk.
2. Leave the app on the home screen with no modals open.
3. Final report (Korean, under 120 words): counts per verdict, TC IDs + headline of 「문제」 rows, new blockers, average minutes per row, anything that made you stop early.

## Rejection rule (added 2026-10-10 after batch-005)
A batch where several rows share one screen check, one unmarked figure or identical started_at/ended_at is rejected and re-run. Do each row's own steps, figure and `date` stamps before moving on. Rows whose earlier verdict was 「문제」 and now differ must quote the document clause and what you saw.

## DEV outages (added 2026-10-10)
DEV had short outages at ~10:50 and ~11:12 on 2026-10-10. If a list fails, check once whether another menu's list (e.g. 「고객」 회원 ID) also fails. If both fail it is a DEV outage: wait 3 minutes and retry up to 3 times, then record `실행 불가` with the times and stop the batch with a report. If only one screen fails, follow the backend-outage rule of the skill and continue.
