# wrxp 효과 실측 벤치마크 · 핸드오프

작성: 2026-11-09 22:58 KST(사용자 시간대 추정, UTC 13:58) · 세션 0717732f-216e-5d96-be1b-25ee0c15e48c(클라우드) · 프로젝트 폴더: 저장소 루트 `claude-middleware`(브랜치 `ccr-19908822-0fhs21`) · 이전 핸드오프: 없음

## 0. 재개 방법

- 첫 행동:
  1. `git fetch origin ccr-19908822-0fhs21 && git checkout ccr-19908822-0fhs21`로 브랜치를 받는다.
  2. 사용자가 로컬 브라우저(로그인된 Hugging Face 계정)에서 https://huggingface.co/datasets/cais/hle-diamond 이용 조건에 동의하고 parquet 파일을 받았는지 확인한다. 받았다면 그 파일 경로를 묻는다. 로컬에서는 `huggingface-cli login`이나 `HF_TOKEN` 환경 변수로 직접 받아도 된다(토큰은 사용자가 로컬에서 설정한다).
  3. §2-2의 "HLE-Diamond 실험"을 진행한다. 실행 전 예상 비용(60~90달러)을 사용자에게 알리고 진행 여부를 확인한다. 이 실험의 예산은 아직 승인되지 않았다.
- 다시 하지 말 것:
  - 1~4차 실험과 1순위 지표 재분석은 끝났다. 결과는 `benchmarks/wrxp-spec-test/results/` 아래 각 폴더의 `RESULTS.md`에 있다.
  - "메인 크롬 프로필에 디버그 포트를 붙여 띄우기"는 하지 않는다. 클라우드 세션이라 불가능했고, 크롬 136 이후 기본 프로필에서는 원격 디버깅 스위치가 무시된다(보안상 위험도 있음). 사용자가 직접 파일을 받는 방식으로 정리했다.
  - 사용자는 Hugging Face 토큰을 클라우드 환경에 저장하는 것을 거절했다(D13). 다시 요청하지 않는다.
- 상태 확인: `git log --oneline -6` (최신 커밋이 이 핸드오프 커밋), `python3 -m unittest discover -s wrxp/tests -q` (마지막 결과 159건 OK).
- 이어받는 쪽: 이전 요약은 사람 결정의 원문이 아니다. 결정 주장은 원 기록에서 확인한다.
- 이어받는 쪽: 완료 주장은 실제 결과로 다시 확인하되 끝난 조사는 반복하지 않는다.

## 1. 사용자 의도

### 1-1. 최초 의도

"wrxp플러그인의 스펙테스트 지표를 뽑고싶음. 베이스라인과 wrxp적용시 차이를 다양한 지표를 통해 측정하고싶다. 측정후에는, 회사의 각 업무/개발/기획/마케팅/디자인 등에서 어떤 객관적 지표가 있을지 차이는 얼마인지 베이스라인과 차이 비교해보자" (0717732f:U1)

### 1-2. 작업 중 결정

| # | 결정 | 사용자 원문 (출처) | 계기 |
|---|---|---|---|
| D1 | 전역 CLAUDE.md(wrxp:setup 산출물) 있음/없음을 변인에 넣어 wrxp 적용/미적용과 2×2(최소 4케이스)로 측정 | "전역클로드.md도 셋업에 있음을 잊지말고 이것도 변인으로 넣어서 뽑아줭 … 최소 4케이스겠네" (0717732f:U2) | 1차 결과 보고 후 |
| D2 | 모델 지능을 재는 표준 지표(Recall@5, MMLU 등)를 최소 5~10개 넣는다 | "리콜@5 막이런거 … mmlu이런거였나? 이런것들도 최소5개 10개는 했음좋겠음" (0717732f:U2) | 같음 |
| D3 | 답변은 한국어로 | "한국어로해줘" (0717732f:U3) | 영어 답변에 대해 |
| D4 | 어려운·조율이 필요한 과제로 다시 측정, 예시 없이 바로 진행, 예산 200달러 | "예시 없이 바로 진행해, 예산 200달러" (0717732f:U5) | AI가 "실제 체감 작업 예시를 주면 좋다"고 제안한 데 대한 답 |
| D5 | 표본을 몇 배로 늘리고, pstack과 비교하고, 마케팅·재무·기획 등 다양한 사용 시나리오를 넣고, 공신력 있는 최신 벤치마크를 넣는다 | "표본 몇배로 늘리고, pstack 이랑도 벤치마크 해보자 … 신기한벤치들 … 그런거 하라는말임" (0717732f:U6) | — |
| D6 | 4차 예산 약 700달러 | 질문 답 "약 700달러 (권장)" (0717732f:U7) | AI의 예산 질문 |
| D7 | pstack 조건은 단독 설치 + `/pstack:poteto-mode` 명시 호출 두 가지 | 질문 답 "단독 + /poteto-mode 명시 호출" (0717732f:U7) | AI 추천은 단독만 |
| D8 | 공개 벤치마크는 τ²-bench, Terminal-Bench 2, SWE-bench Verified | 질문 답 "['τ²-bench (권장)', 'Terminal-Bench 2', 'SWE-bench Verified']" (0717732f:U7) | — |
| D9 | wrxp 강점을 나타내는 지표를 모두 찾아 리뷰하고, 1순위부터 적용 | "강점들에 대해서 나타낼 수 있는 지표를 모두찾고 … 정리해보자" (0717732f:U11), "1순위부터하자" (0717732f:U12) | AI의 우선순위 제안에 대한 답 |
| D10 | 결과를 한국어 상세 보고서 웹페이지로 | "한국어로 재답변하고, 웹페이지로 잘 다듬어서 상세보고서 뽑아줘" (0717732f:U15) | — |
| D11 | wrxp 강점 위주(편파적)의 소개 HTML 페이지를 만들고, Notion 개인 비공개 페이지로도 올린다 | (0717732f:U16), "노션 개인비공개 페이지로 올려줄수있나?" (0717732f:U17) | — |
| D12 | 다음 측정은 최근 1주일 새 나온 지능 측정 벤치마크로 한다. reasoning framework 강제 적용 실험("어려운 거 생각하게")도 함께 고려 | "너가 강제로 reasoning framework 적용해서 어려운거 생각하게 해볼래?" (0717732f:U19), "ai지능 측정하는거 최근1주일새 새거 나온거같던데 그걸로하면어떨까함" (0717732f:U21) | U19 진행 중 중단(U20) 후 U21 |
| D13 | Hugging Face 토큰을 클라우드 환경에 저장하지 않는다 | 자격 증명 요청을 거절("User declined to provide the secret") | HLE-Diamond 다운로드용 토큰 요청에 대해 |
| D14 | 작업을 다른 로컬 환경으로 옮겨 이어 간다 | "핸드오프하게 써줘 다른로컬에서할거" (0717732f:U23) | 크롬 디버그 포트 방식이 클라우드에서 불가하다는 답 이후 |

참고(결정 아님): U18에서 사용자는 "맨앞만 읽는 AI 툴 때문에 wrxp 스킬 내용이 버려지지 않냐, 개선하려고 한다"고 물었고, AI는 실행 기록 분석 결과(§2-1)를 보고했다. 개선 착수 여부는 결정되지 않았다.

### 1-3. 최종 의도

wrxp의 효과를 객관 지표로 측정해 회사 업무별로 설명할 수 있게 하고, 그 결과로 wrxp를 개선한다. 지금 단계에서는 최근 나온 고난도 지능 벤치마크로 wrxp(특히 reasoning framework를 강제로 적용했을 때)가 어려운 추론을 돕는지 측정하려 하며, 이 작업을 다른 로컬 환경에서 이어 간다.

## 2. AI 기획

### 2-1. 핵심 포인트

- **조건 설계:** 조건마다 별도의 `CLAUDE_CONFIG_DIR`를 써서 차이를 setup 산출물과 플러그인에만 한정했다(`benchmarks/wrxp-spec-test/conditions.py`). 전역 조건은 `setup_global.py --apply`의 실제 출력을 쓴다.
- **측정 결과 요지:**
  - 표준·공개 벤치마크(MMLU-Pro, GPQA, SWE-bench Verified 등)는 조건 간 차이가 없었다(천장).
  - 숨은 의도가 있는 부서 시나리오 15개에서 haq/haqq의 첫 납품 점수가 +22/+28%p 올랐다. 다만 약 30%는 모의 사용자의 과잉 공개 덕분이므로 상한값이다.
  - 주된 작동 경로는 "작업 전 기본값 미리 보여 주기"였다.
  - 상세: `benchmarks/wrxp-spec-test/results/report/wrxp-report.html`, `results/2026-11-07-tier1/RESULTS.md`
- **U18 분석(스킬 내용이 버려지는가):** 부서 시나리오 360회 기록을 분석한 결과다.
  - `ha/SKILL.md` 본문은 끝까지 들어간다. 펼쳐진 내용 9,204자가 본문 8,679자를 포함한다.
  - `references/questioning.md`는 질문할 때 대체로 읽힌다(78/120).
  - `shared/reasoning-framework.md`, `shared/writing-rules.md`, `references/tracks.md`, `verification.md`, `model-routing.md`는 0회 읽혔다.
  - 개선안(보고만 함, 미승인):
    1. 필수 줄은 본문으로 옮긴다.
    2. 참조 문서를 열 조건을 행동으로 쓴다.
    3. 결정을 바꾸는 규칙은 앞쪽으로 옮긴다.
    4. description을 250자 안팎으로 줄이고, WorxSales QA 7개를 분리하는 방안을 검토한다.
    5. 참조 문서가 실제로 읽히는 비율을 벤치마크 지표로 고정한다.
- **최근 1주일 새 벤치마크 조사(2026-11-09):**
  - **GDPx(SemiAnalysis, 11/2):** 206개 장시간 에이전트 과제, 최고 12%. 과제가 대부분 비공개이고 과제당 제한이 8시간이라 실행할 수 없다고 판단했다.
  - **HLE-Diamond(CAIS·Scale, Artificial Analysis Intelligence Index v5에 편입):** 1,000문항(추론 500, 지식 500), Opus 5.5(max) 68%.
    - 천장이 아니어서 차이를 볼 수 있다.
    - Hugging Face `cais/hle-diamond`에 있다. 로그인과 이용 조건 동의가 필요하고, 안내문에 재배포 금지가 적혀 있다.
  - 근거 링크: https://huggingface.co/datasets/cais/hle-diamond , https://x.com/ArtificialAnlys/status/2115989388689813945 , https://aicoder.com/news/news-20261102-semianalysis-gdpx-agentic-benchmark-206-tasks-11-domains-opus-5-5-tops-12-percent

### 2-2. 최종 기획

- **HLE-Diamond 실험** — 미승인·보고함(사용자가 U21에서 방향은 제안, 구체안과 비용은 미승인)
  - 추론 파티션에서 고정 시드로 100문항을 뽑는다. 이미지 문항 포함 여부는 미정이며, 텍스트만 쓰는 쪽이 단순하다.
  - 조건 3개:
    - `base`
    - `global_haqq`
    - `global_haqq_rf`: wrxp 복사본의 `ha/SKILL.md` 앞쪽에 `shared/reasoning-framework.md` 전문을 넣고, "COMMIT_INTENT 전과 납품 전에 반드시 적용한다"는 단계를 추가한 변형판.
  - 실행: `claude -p` 1회, 도구 없이(Artificial Analysis 방식) 또는 기존 `std` 수트와 같은 도구 권한. 둘 중 무엇을 쓸지는 미정이다.
  - 채점: pass@1, 정답 동치를 LLM으로 판정한다. 기존 `std/grade_std.py`의 `llm_equiv` 방식을 재사용할 수 있다.
  - 예상 비용 60~90달러(300회).
  - 데이터 처리: 문항과 정답은 커밋하지 않는다. 문항 ID와 채점 결과만 커밋하고, 원본은 `.gitignore`된 경로에 둔다.
- **reasoning framework 강제 적용 실험** — 요청 범위(U19), 착수 전 중단
  - 처음 계획은 부서 시나리오 중 질문으로 풀리지 않는 5개(inventory, dev-api-migration, cs-macro, roadmap, mkt-campaign)를 4회씩 돌리고, 기존 `global_haqq` 기록을 대조군으로 쓰는 것이었다(약 25~35달러).
  - U21 이후 HLE-Diamond로 대상을 옮기는 쪽으로 이야기가 진행됐다. 두 실험을 모두 할지는 미정이다.
- **변형판 플러그인 만드는 법(아직 만들지 않음)**
  1. `wrxp/`를 `benchmarks/wrxp-spec-test/.cache/wrxp-rf/`로 복사하고 `ha/SKILL.md`만 고친다.
  2. `conditions.py`에 `global_haqq_rf` 조건을 추가한다. 플러그인 경로는 변형판을 가리키고, 전역 블록은 원본 setup 출력을 그대로 쓴다.

## 3. 현재 상태

- **완료:** 1차(84회), 2차 2×2와 표준 벤치마크 10종(964회), 3차 고난도·대화형(75회), 4차 pstack·부서 시나리오 15개·τ²-bench·SWE-bench Verified·Terminal-Bench 2(648회), 1순위 지표 재분석(360회 판정)
  - 근거: 커밋 `2f8d078` 이후 `41ba4e2`까지, `benchmarks/wrxp-spec-test/results/*/RESULTS.md`
  - 누적 실행 비용 약 850달러(판정 비용 별도)
- **완료:** 상세 보고서·소개 페이지 HTML. 원본은 `benchmarks/wrxp-spec-test/results/report/`에 있다(wrxp-report.html, wrxp-intro.html, build_report.py).
- **진행 중:** HLE-Diamond 데이터 확보. Hugging Face 접속은 열렸으나(§3-1) 데이터셋이 로그인 필요라 받지 못했다. 사용자가 토큰 저장을 거절했고 다른 로컬에서 진행하기로 했다.
- **미착수:** HLE-Diamond 실험, reasoning framework 변형판, U18 개선안 적용, 엄격한 모의 사용자 재측정, 명확한 쌍둥이 과제(불필요한 질문·과잉 차단율), `/ha` 결과 틀 수정(IFEval −7.5%p)

### 3-1. 세션 종속 자원과 외부 변경

- **세션이 끝나면 사라지는 것:** 클라우드 세션 임시 폴더(scratchpad)
  - 실행별 전체 대화 기록과 작업 폴더 스냅숏(`hard2/`, `std/`, `tau2/`, `swe/`, `tb2/` 등)이 있다. 요약·채점 결과와 실행별 `result.json`, `grade.json`, `tier1.json`은 저장소 `results/`에 복사돼 있다.
  - 전체 대화 원문(`agent*.jsonl`)과 스냅숏은 저장소에 없다. 다시 분석하려면 재실행해야 한다.
- **세션 밖에서 계속 동작하는 것:** 없음. 백그라운드 작업과 예약 작업 없음.
- **외부에 이미 반영한 것:**
  - GitHub: 브랜치 `ccr-19908822-0fhs21`에 커밋·푸시(PR은 만들지 않음).
  - claude.ai 아티팩트 3개(모두 비공개):
    - 대시보드 https://claude.ai/artifact/9fir144Ju2cG4VKCW1m5U2
    - 상세 보고서 https://claude.ai/artifact/4iKjeqfcszDZVpdPnpHsUc
    - 소개 페이지 https://claude.ai/artifact/5GCxKMt3gEVjbvBYUvgaMc
  - Notion: 개인 비공개 초안 "wrxp 소개: 말하지 않은 의도까지 처음부터 맞춥니다" https://app.notion.com/p/4117d8322b0481c8a5f3d68d0191d92c
  - Claude Code 클라우드 환경: 개인 환경 `claude-middleware`(env_01B9HwnCJXJoooAXaP5u3jMH)를 새로 만들었다. 허용 호스트는 huggingface.co와 HF CDN 3개이고, 이 세션이 그 네트워크로 이동했다. 기본 환경은 바꾸지 않았다.

## 4. 문제점

- **HLE-Diamond를 받지 못함.** 근거: API 응답 `"gated":"auto"`. 원인(확인됨): 로그인과 이용 조건 동의가 필요하고, 토큰이 없다(D13).
- **로컬에서 재현할 때 필요한 설치.** 근거: 이 세션에서 겪은 오류.
  - `pip install tau2`는 엉뚱한 패키지가 깔린다. τ²-bench 저장소(`sierra-research/tau2-bench`)를 받아 `pip install -e .`로 설치해야 한다.
  - Python 3.13에서는 `audioop-lts`가 필요하다.
  - `mcp`는 2.x의 API가 달라서 `pip install "mcp<2"`로 1.x를 써야 한다.
  - `langdetect`는 빌드가 실패해 원본 tar를 풀어 site-packages에 복사했다.
  - nltk `punkt`·`punkt_tab`은 nltk 다운로더가 막혀 GitHub raw에서 직접 받았다.
  - pstack은 `benchmarks/wrxp-spec-test/fetch_pstack.sh`로 받는다.
  - Terminal-Bench 2 과제 폴더(`tbench/tasks/`)는 커밋하지 않았다. 가짜 비밀 문자열이 들어 있어 GitHub 비밀 검사에 막혔기 때문이다. `tbench/make_tasks.py`로 terminal-bench-2 저장소 클론에서 다시 만든다.
- **모의 사용자(Sonnet)가 지시를 어기고 묻지 않은 내용을 먼저 말함.** 근거: `results/2026-11-07-tier1/RESULTS.md`, 과잉 공개 30%. 원인(가설): 지시 준수 한계. 엄격한 모의 사용자로 다시 재야 한다.

## 5. 미결 사항

- HLE-Diamond 실험 진행 여부와 예산(AI 제안 60~90달러), 문항 수, 도구 허용 여부, 이미지 문항 포함 여부
- reasoning framework 변형 실험을 부서 시나리오에서도 할지(약 25~35달러)
- U18 개선안(스킬 구조 정리)을 실제로 적용할지, 어떤 항목부터 할지
- 엄격한 모의 사용자 재측정과 2순위 지표(150~250달러)를 진행할지
- 사용자 시간대(KST로 추정했음)
