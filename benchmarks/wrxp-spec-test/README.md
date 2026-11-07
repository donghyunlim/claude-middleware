# wrxp spec test

이 폴더는 같은 과제를 wrxp 적용 여부별로 실행하고 객관 지표로 비교하는 실측 벤치마크입니다. 과제는 두 묶음입니다. 하나는 부서별 실무 과제 14개이고, 다른 하나는 공개 표준 벤치마크 10종입니다.

- **wrxp vs pstack 확장 실측(부서 시나리오 15개, τ²-bench, SWE-bench Verified, Terminal-Bench 2): [results/2026-11-07-full/RESULTS.md](results/2026-11-07-full/RESULTS.md)**
- 고난도·대화형 결과(모의 사용자, haq·haqq 포함): [results/2026-11-06-hard/RESULTS.md](results/2026-11-06-hard/RESULTS.md)
- 4조건 결과(전역 CLAUDE.md × `/wrxp:ha`): [results/2026-11-06-2x2/RESULTS.md](results/2026-11-06-2x2/RESULTS.md)
- 첫 2조건 결과(baseline × `/wrxp:ha`): [results/2026-11-06/RESULTS.md](results/2026-11-06/RESULTS.md)

## 조건 (2×2)

변인은 두 개입니다. 첫째는 `wrxp:setup`이 설치하는 전역 CLAUDE.md 블록과 플러그인 폴더 읽기 허용 규칙이고, 둘째는 `/wrxp:ha` 호출입니다. 정의는 [conditions.py](conditions.py)에 있습니다.

| 조건 | 전역 CLAUDE.md·settings | 플러그인 로드 | 과제 문장 앞 |
|---|---|---|---|
| `base` (미적용) | 없음 | 없음 | - |
| `global` (전역만) | 있음 | 있음 | - |
| `ha` (/ha만) | 없음 | 있음 | `/wrxp:ha` |
| `global_ha` (전역+/ha) | 있음 | 있음 | `/wrxp:ha` |

- 조건마다 별도의 `CLAUDE_CONFIG_DIR`를 씁니다. 전역 조건의 설정 폴더에는 `setup_global.py --apply`의 실제 출력이 들어갑니다. 그래서 조건 사이의 차이는 setup 산출물뿐입니다.
- 전역 조건은 플러그인도 불러옵니다. setup은 플러그인이 설치되어 있다고 전제하고, 전역 규칙이 wrxp 스킬로 연결되기 때문입니다.
- 주효과는 2×2 평균 차이로 계산합니다. 전역 효과는 (전역만+전역+/ha)/2 − (미적용+/ha만)/2이고, /ha 효과도 같은 방식입니다.

## 설계

- **조건:** 두 조건 모두 같은 모델, 같은 권한, 같은 과제 문장을 씁니다. baseline은 `claude -p`를 그대로 실행합니다. wrxp는 `--plugin-dir wrxp`로 플러그인을 불러오고, 과제 문장 앞에 `/wrxp:ha`를 붙입니다. 이 저장소의 `AGENTS.md`가 실행에 섞이지 않도록 작업 폴더는 저장소 밖에 만듭니다.
- **격리:** 실행마다 fixture를 새로 복사합니다. 숨긴 테스트·정답·채점표(`tasks/*/hidden/`)는 작업 폴더에 들어가지 않습니다.
- **채점:**
  - 코드 과제는 숨긴 pytest로 채점합니다.
  - 수치 과제는 정답값과 일치하는지 봅니다.
  - 마케팅 문안은 글자 수·금지어·근거 없는 수치를 규칙 검사기로 확인합니다.
  - 디자인 과제는 Playwright로 명암비·레이블·오류 연결·포커스·가로 스크롤을 확인합니다.
  - 운영 과제는 파일 보존 여부를 확인합니다.
  - 문서·보고 과제(PRD, CS 답장, 조사, 검증 불가 보고)는 블라인드 LLM 채점자가 채점합니다. 채점자는 자료, 채점표, 산출물만 보고, 산출물이 어느 조건에서 나왔는지 모릅니다.
- **실행 지표:** stream-json 기록에서 비용, 시간, 턴, 출력 토큰, 도구 호출, 검증 실행 횟수, 응답 언어를 뽑습니다.

## 부서별 과제

| id | 부서 | 측정하는 것 |
|---|---|---|
| dev-bug | 개발 | 증상과 다른 곳에 있는 근본 원인, 호출부 땜질 제거 |
| dev-feature | 개발 | 명세 경계 조건(거부 규칙 14개) |
| dev-refactor | 개발 | 반올림·음수 같은 기벽까지 동작 보존(골든 84건) |
| plan-prd | 기획 | 일정 충돌·미결정 노출, 지어낸 수치 |
| data-revenue | 데이터·재무 | KST 경계·중복·테스트 계정·금액 누락 함정 |
| mkt-copy | 마케팅 | 채널 규격·심의 금지어·출처 표기 |
| design-form | 디자인 | 명세 토큰 중 AA 미달 색(#A0A7B0) 함정, 접근성 |
| ops-cleanup | 운영·인프라 | 보관 정책, legal hold 보호 |
| research-retry | 조사·분석 | 설정 3겹 덮어쓰기 + off-by-one, 낡은 문서 |
| cs-reply | CS | 권한 밖 약속 금지, 정책 적용 |
| hard-migration | 개발·DBA | 승인 없이 운영 DB를 바꾸지 않는가 |
| hard-sibling | 개발 | 재발 버그와 같은 패턴 두 곳 |
| hard-unverifiable | 개발·운영 | 확인할 수 없는 것을 확인했다고 말하지 않는가 |
| hard-data-conflict | 데이터·경영지원 | 정의가 바뀐 대시보드 수치를 그대로 쓰지 않는가 |

## 표준 벤치마크

[std/prepare_data.py](std/prepare_data.py)가 원 배포처(GitHub, S3)에서 데이터를 받아 벤치마크마다 고정 시드로 20문항씩 뽑습니다. 문항은 `std/items/`에 있고, 문항 하나를 `claude -p` 한 번으로 실행합니다. 도구 사용 조건은 부서별 과제와 같으며, 웹 검색 도구는 허용하지 않습니다.

| 벤치마크 | 영역 | 지표 | 채점 |
|---|---|---|---|
| MMLU-Pro | 지식·추론(10지선다) | 정확도 | 마지막 `ANSWER:` 줄의 선택지 |
| GPQA Diamond | 대학원 과학(4지선다, 선택지 섞음) | 정확도 | 같음 |
| MATH-500 | 수학 | 정확도 | 정규화 일치, 불일치 때만 LLM 동치 판정 |
| GSM8K | 초등 수학 서술형 | 정확도 | 수치 일치 |
| BIG-Bench Hard | 다단계 추론(과제 20종에서 1문항씩) | 정확 일치 | 정규화 일치 |
| HumanEval | 코드 생성 | pass@1 | 원 테스트 `check()` |
| MBPP | 코드 생성 | pass@1 | 예시 1개만 보여 주고 전체 테스트 |
| IFEval | 지시 이행 | 프롬프트 strict 정확도(보조: loose, 지시 단위) | Google 공식 채점 코드(`std/ifeval_lib`, Apache-2.0) |
| TruthfulQA MC1 | 사실성·환각 | 정확도 | 선택지 섞음 |
| SciFact (BEIR) | 문서 검색(초록 5,183개) | Recall@5(보조: Recall@10, nDCG@10, MRR@10) | 정답 근거 문서 대비 순위 |

## 실행

```bash
pip install pytest pyyaml absl-py nltk immutabledict   # 모든 조건이 같은 도구를 쓰도록 먼저 설치
python3 std/prepare_data.py --cache CACHE --n 20       # 표준 벤치마크 문항 준비
python3 run.py --suite dept --out DEPT --reps 3 --parallel 5
python3 run.py --suite std  --out STD  --parallel 8 --timeout 900
python3 grade.py DEPT --judge && python3 aggregate.py DEPT > DEPT/tables.md
python3 std/grade_std.py STD && python3 std/aggregate_std.py STD > STD/tables.md
```

- `run.py`는 이미 끝난 실행을 건너뜁니다.
- IFEval 채점에는 `langdetect`와 nltk `punkt`·`punkt_tab`이 필요합니다.
- 첫 2조건 실행 84회의 실행 비용은 약 24달러였고, 채점자 호출 비용은 따로 듭니다.

## 고난도·대화형 과제 (hard/)

숨은 의도를 묻지 않으면 틀리는 과제와 조율이 필요한 과제 5개를 `hard/tasks/`에 두었습니다. 과제마다 `intent.md`(모의 사용자만 아는 의도)가 있습니다. [hard/run_hard.py](hard/run_hard.py)는 다음 순서로 진행합니다.

1. 에이전트에게 과제를 줍니다.
2. 모의 사용자(Sonnet 5.5, 도구 없음)가 에이전트의 메시지를 읽고 질문에 답하거나, 수정을 요청하거나, 수락합니다.
3. 에이전트는 같은 세션을 `--resume`으로 이어 가며, 이 과정을 최대 3번 반복합니다.

에이전트가 응답할 때마다 작업 폴더를 저장하므로 첫 납품과 최종 결과를 따로 채점할 수 있습니다.

```bash
python3 hard/run_hard.py --out HARD --reps 3 --parallel 6
python3 hard/grade_hard.py HARD && python3 hard/aggregate_hard.py HARD > HARD/tables.md
```

## pstack 비교와 공개 에이전트 벤치마크

- `./fetch_pstack.sh`가 pstack(0.9.132, 커밋 고정)을 `.cache/`에 받습니다. 조건 `pstack`과 `pstack_poteto`가 이를 씁니다.
- **τ²-bench:** τ²-bench 저장소를 받아 `pip install -e .`로 설치합니다. 이때 `audioop-lts`와 `mcp<2`도 함께 설치해야 합니다. 실행은 `python3 tau2/run_tau2.py --out TAU2`, 집계는 `python3 tau2/aggregate_tau2.py TAU2`입니다. 도메인 도구는 [tau2/tau2_mcp.py](tau2/tau2_mcp.py)가 MCP로 노출하고, 채점은 τ²-bench의 DB 평가기를 그대로 씁니다.
- **SWE-bench Verified:** 순서는 `swebench/prepare_instances.py` → `validate.py` → `run_swe.py --out SWE`이고, 집계는 `python3 aggregate_resolve.py SWE "SWE-bench Verified"`입니다. Docker와 `pip install swebench`가 필요합니다.
- **Terminal-Bench 2:** 순서는 `tbench/make_tasks.py` → `python3 tbench/tb_env.py kit` → `validate.py` → `run_tb2.py --out TB2`이고, 집계는 `python3 aggregate_resolve.py TB2 "Terminal-Bench 2"`입니다. Docker가 필요합니다.
