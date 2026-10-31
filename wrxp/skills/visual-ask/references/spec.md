# spec.json 형식

`build.py`가 읽는 결정 페이지 정의입니다. 상대 경로는 spec.json이 있는 폴더를 기준으로 읽습니다.

```json
{
  "id": "ui-polish-2026-10",
  "title": "화면 다듬기 리뷰",
  "note": "브랜치 feature/ui-polish · 그룹마다 커밋 1개 · 아직 push 전",
  "kind": "approve",
  "sections": [
    {
      "title": "G1 홈",
      "badge": "dcb9c080",
      "pages": [
        {
          "id": "home",
          "title": "홈",
          "summary": "카드 간격과 보조 글자 크기를 맞췄습니다.",
          "notes": [
            { "title": "바꾼 것", "items": [{ "text": "카드 사이 16px", "why": "붙어 보여서" }] },
            { "title": "하지 않은 제안 2개", "collapsed": true, "items": ["상단바 두 줄 접힘"] }
          ],
          "items": [
            {
              "id": "default",
              "title": "기본 상태",
              "options": [
                { "id": "before", "label": "수정 전", "image": "shots/home-before.png" },
                { "id": "after", "label": "수정 후", "image": "shots/home-after.png" }
              ]
            },
            {
              "id": "empty-layout",
              "kind": "choose",
              "title": "빈 상태 배치",
              "question": "목록이 비었을 때 안내를 어디에 둘까요?",
              "recommend": "b",
              "options": [
                { "id": "a", "label": "A 표 안", "image": "mock/a.png" },
                { "id": "b", "label": "B 가운데", "html_file": "mock/b.html", "height": 420 },
                { "id": "c", "label": "C 안내 없음", "text": "빈 표만 보여 줍니다." }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

## 필드

| 위치 | 필드 | 뜻 |
|---|---|---|
| 최상위 | `title` (필수) | 페이지 제목과 브라우저 탭 이름 |
| | `id` | 브라우저 저장 키. 없으면 `title`에서 만듭니다. 같은 리뷰를 다시 빌드할 때는 바꾸지 않습니다. |
| | `note` | 왼쪽 레일 위 안내(브랜치, 촬영 방식 등) |
| | `kind` | 항목 기본 종류. `approve`(기본값) 또는 `choose` |
| | `mark` | 레일 로고 글자. 없으면 제목 첫 글자 |
| section | `title`, `badge` | 레일의 묶음 제목과 오른쪽 작은 표시(커밋 등) |
| page | `id` (필수), `title`, `badge`, `summary`, `notes` | 레일의 링크 하나이자 본문 한 화면. `notes`는 `{title, items, collapsed}` 목록이고, `items`는 문자열 또는 `{text, why}`입니다. |
| item | `id` (필수), `title`, `kind`, `question`, `recommend`, `rev`, `options` | 결정 카드 하나. 저장 키는 `페이지id__항목id`입니다. |
| option | `id`, `label`, 그리고 `image`·`html_file`·`html`·`text` 중 하나, `height` | `html` 시안은 스크립트 없이 격리된 틀에 그리며, `height`(기본 360px)로 높이를 정합니다. |

## 규칙

- 페이지 id와 항목 저장 키는 전체에서 겹치면 안 됩니다. `build.py`가 겹침, 없는 그림, 선택지가 1개뿐인 `choose`, 선택지에 없는 `recommend`를 오류로 막습니다.
- `approve` 항목에 선택지가 2개이면 첫 번째를 수정 전, 두 번째를 수정 후로 보고 처음에는 수정 후를 보여 줍니다. 수정 후만 있는 새 화면은 선택지 1개로 둡니다.
- 고친 항목을 다시 물을 때는 `rev`를 올립니다. 키를 바꾸면 이전 답과의 연결이 끊깁니다.
- 그림은 `--max-width`, `--jpeg`로 줄일 수 있습니다. macOS의 `sips`나 Pillow가 있을 때만 줄이고, 둘 다 없으면 원본을 복사합니다.
