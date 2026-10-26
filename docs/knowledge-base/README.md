# 지식 베이스 만들기

시민이 무엇을 알고 어디서 이야기를 시작하는지는 시민에게 넣어 주는 재료, 곧 지식 베이스가 정합니다. 그 위에서 대화를 만들어 가는 것은 모델입니다. 이 문서들은 그 재료를 구성하는 방법을 다룹니다. 기능별 사용법은 [실행 예제(recipes)](../recipes)에 따로 있습니다.

> 예시 지식 베이스의 데이터는 모두 설명을 위해 만든 **가상 데이터**입니다. 실제 기관·서비스·작품과 관계없습니다.

## 지식 베이스란

시뮬레이션 한 번에 필요한 입력 전체를 말합니다. 다섯 가지로 나뉘고, 각각 시민 프롬프트의 정해진 칸으로 들어갑니다.

| 구성 요소 | 파일 | 무엇을 담나 | 프롬프트에서 |
|---|---|---|---|
| 주제 정보 (digest) | `digest.json` | 소식의 요약과 확인된 사실 목록 | `[알고 있는 것]` |
| 쟁점 카드 (cards) | `cards.json` | 사람들이 이 소식을 두고 꺼낼 만한 관심사·질문·전해 들은 얘기 | `[관심사]`, `[들은 얘기]` |
| 대상 (target) | `meta.json` | 이 소식이 누구에게 해당하는지 | 시민과 소식의 관계, 발언 순위 |
| 시민 (personas) | `personas.json` | 대화에 참여할 사람들의 사실 정보 | `[나]`, `[내 처지]` 등 |
| 주제 문구·사양 | `meta.json` | 소식을 부르는 말, 상태 어휘, 프롬프트 사양 이름 | 머리표, 규칙 |

사실(주제 정보)과 의견(쟁점 카드)을 나누는 것이 가장 중요한 원칙입니다. 이유와 나머지 원칙은 [01](01-knowledge-base.md)에 있습니다.

## 문서

| 문서 | 내용 |
|---|---|
| [01. 지식 베이스 구성 방법](01-knowledge-base.md) | 재료와 모델이 각각 하는 일, 도메인별로 넣을 것, 원칙 7가지, 작업 순서 |
| [02. 주제 정보 만들기](02-digest.md) | 사실 고르는 기준, 상태 어휘, 점검 목록 |
| [03. 쟁점 카드 만들기](03-cards.md) | 수집 소스, 카드 필드, 다양성 확보, 관련성 판정 |
| [04. 시민 구성하기](04-personas.md) | 시민 필드, 도메인 속성 넣는 칸, 상황 태그, 공개 데이터셋 |
| [05. 주제 문구와 사양](05-topic-and-spec.md) | Topic 설정, 사양 선택, 모델 고르기 |
| [06. 자주 생기는 문제](06-pitfalls.md) | 증상별 원인과 대응 |

## 빠른 시작

도구는 `examples/kb_tools/`에 있고, `examples` 폴더에서 실행합니다.

```bash
cd examples
python -m kb_tools.validate knowledge-bases/local-news          # 형식·구성 점검
python -m kb_tools.run knowledge-bases/local-news --fake --msgs 12   # 모델 없이 흐름 확인
python -m kb_tools.run knowledge-bases/local-news --msgs 40          # 실제 모델 (SARANGBANG_* 환경 변수)
```

실행 결과는 `examples/out/<이름>/`에 메시지(`messages.jsonl`)와 시민별 프롬프트(`prompts.json`)로 저장됩니다. 프롬프트 파일을 열어 시민에게 실제로 무엇이 들어갔는지 확인하는 것을 권장합니다.

## 도구

| 명령 (`examples` 폴더에서) | 하는 일 |
|---|---|
| `python -m kb_tools.extract_digest 문서.txt -o digest.json --title "..."` | 소식 원문에서 주제 정보(요약·사실)를 LLM으로 뽑습니다 |
| `python -m kb_tools.make_cards 수집글.jsonl -o cards.json --title "..."` | 수집한 글·댓글에서 쟁점 카드를 LLM으로 만듭니다 |
| `python -m kb_tools.validate <폴더>` | 형식 오류와 구성 문제(찬반 쏠림, 맞는 시민이 없는 카드 등)를 점검합니다 |
| `python -m kb_tools.run <폴더> [--fake]` | 관련성 판정 → 연결 의견 → 카드 배분 → 단톡방 실행 → 결과 저장 |
| `python -m kb_tools.export <폴더> -o 시나리오.json` | 시나리오 파일 하나로 내보냅니다(`sarangbang run`으로 실행) |

추출 도구의 프롬프트는 비교 시험을 거치지 않은 출발점입니다. 결과를 사람이 검수한 뒤 쓰세요.

## 시나리오 파일과의 관계

[시나리오 파일](../../README.md#시나리오-파일)은 같은 내용을 JSON 한 파일에 담은 것입니다. 지식 베이스 폴더는 파일을 나눠 사람이 작성·검수하기 쉽게 한 형식입니다.

| | 시나리오 파일 | 지식 베이스 폴더 |
|---|---|---|
| 형태 | JSON 한 파일 | `meta` · `digest` · `cards` · `personas` · `relevance` 파일로 나눔 |
| 실행 | `sarangbang run 시나리오.json` | `python -m kb_tools.run <폴더>` |
| 주제 문구 | `generic` / `policy` 중 선택 | 선택 + 머리표·관계 칸 이름·주제 일반어(`common_words`) 바꾸기 |
| 연결 의견(카드와 소식을 잇는 한 줄) | 만들지 않음 | 실제 모델 실행 때 LLM으로 만듦 |
| 관련성 판정이 없을 때 | 모든 카드를 `direct`로 봄 | LLM으로 판정 |
| 점검 | 없음 | `kb_tools.validate` |

다 만든 뒤 공유할 때는 `kb_tools.export`로 시나리오 파일로 내보냅니다. 시나리오 형식에 없는 항목(바꾼 주제 문구 등)은 빠지고, 무엇이 빠졌는지 안내합니다.

## 예시 지식 베이스

| 폴더 | 소식 | 보여 주는 것 |
|---|---|---|
| [local-news](../../examples/knowledge-bases/local-news) | 공영주차장 야간 유료화 | 이해관계가 갈리는 동네 소식, 거주·영업 상황 태그 |
| [product-launch](../../examples/knowledge-bases/product-launch) | 접이식 스마트폰 출시 | 제품용 상태 어휘(공식 발표·출시 예정·유출·루머), 기존 사용자와 경쟁 제품 사용자 |
| [product-price](../../examples/knowledge-bases/product-price) | 음악 구독 서비스 요금 인상 | 이용자 유형별 관점, 대체 서비스 얘기 같은 바깥 정보 |
| [media](../../examples/knowledge-bases/media) | 웹툰 원작 드라마화와 결말 각색 | 공식 확인·보도·루머 구분, 원작 팬과 일반 시청자 |
| [dating-show](../../examples/knowledge-bases/dating-show) | 연애 예능 한 회 | 찬반이 아니라 여러 갈래 예측이 맞서는 주제, README 데모 화면의 원본 |
| [workplace](../../examples/knowledge-bases/workplace) | 사내 주 4.5일제 시범 운영 | 부서별로 다른 조건, 확정·검토 상태가 섞인 공지 |
| [education-policy](../../examples/knowledge-bases/education-policy) | 초등 돌봄 운영 시간 연장 | 정책 사양(`ko_s12`), 자녀 학년과 대상 관계 |

각 폴더의 README에 무엇을 왜 그렇게 구성했는지 적어 두었습니다.

## 폴더 형식

```
examples/knowledge-bases/<이름>/
├── meta.json        제목, 대상, 주제 문구, 상태 어휘(statuses), 사양, 시민당 카드 수, 방 장면
├── digest.json      주제 정보 {summary, facts[]}
├── cards.json       쟁점 카드 {카드 id: 카드}
├── relevance.json   (선택) 카드 id → direct | related | unrelated. 없으면 실행 때 LLM이 판정
├── personas.json    시민 목록 (DictAdapter 필드)
└── README.md        구성 메모
```
