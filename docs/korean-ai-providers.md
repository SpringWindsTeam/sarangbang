# 국산 AI 모델 사용 가이드

sarangbang은 OpenAI 호환 `/chat/completions`만 쓰므로 **한국어 모델을 어디서 받아 쓰든 같은 코드로 돌아갑니다.** 이 문서는 2026년 10월
기준으로 국산 모델을 쓸 수 있는 경로를 세 갈래로 정리하고, 모델마다 sarangbang에서 주의할 점(추론 모드 끄기, 지원하지 않는 인자, 라이선스)을
적어 둔 것입니다. 모델 이름·가격·제공 여부는 자주 바뀝니다. `sarangbang providers`·`sarangbang models`가 패키지에 들어 있는 최신 표이고,
연결은 `sarangbang doctor`로 확인하세요. 틀린 내용은 [제공처 정보 갱신 이슈](../.github/ISSUE_TEMPLATE/provider_update.yml)로 알려 주세요.

```
sarangbang providers                     # 쓸 수 있는 곳과 환경 변수
sarangbang models [--vendor LG]          # 오픈 웨이트 모델과 vllm serve 힌트
sarangbang doctor --provider upstage     # 키·주소·모델 연결 점검
```

## 한눈에 보기

| 경로 | 무엇 | 준비물 | sarangbang 프리셋 |
|---|---|---|---|
| **국내 기업 API** | 업스테이지 Solar · 네이버클라우드 CLOVA Studio(HyperCLOVA X) | API 키(신용카드·무료 크레딧) | `upstage`, `clova` |
| **중개 플랫폼** | FriendliAI · OpenRouter에 올라온 국산 모델 | 플랫폼 키 | `friendli`, `openrouter` |
| **직접 띄우기** | EXAONE · A.X · K-EXAONE · Solar Open · HyperCLOVA X SEED · Kanana · Mi:dm … 오픈 웨이트 | GPU(또는 노트북 + Ollama) | `vllm`, `sglang`, `ollama`, `lmstudio` |

세 경로 모두 코드는 같습니다.

```python
from sarangbang import get_provider

lane = get_provider("upstage").lane("base", slots=4)                        # UPSTAGE_API_KEY
lane = get_provider("clova").lane("base", model="HCX-DASH-002")             # CLOVASTUDIO_API_KEY
lane = get_provider("vllm").lane("base", model="skt/A.X-4.0-Light")         # http://localhost:8000/v1
lane = get_provider("ollama").lane("base", model="exaone3.5:7.8b")          # http://localhost:11434/v1
```

환경 변수만으로 고르려면 `SARANGBANG_PROVIDER=upstage`(키는 제공처의 환경 변수) 또는
`SARANGBANG_BASE_URL`·`SARANGBANG_API_KEY`·`SARANGBANG_MODEL`(아무 OpenAI 호환 서버)을 두고 `lane_from_env()`를 부릅니다.
앵커 레인(정적 점수 상위 시민용 큰 모델)은 `SARANGBANG_ANCHOR_*`로 따로 둡니다.

## 1. 국내 기업이 직접 운영하는 API

### 업스테이지 Solar — `upstage`

| 항목 | 값 |
|---|---|
| 주소 | `https://api.upstage.ai/v1` |
| 키 | [Upstage Console](https://console.upstage.ai)에서 발급 → `UPSTAGE_API_KEY` |
| 모델 | `solar-pro4`(플래그십, 추론 가능) · `solar-mini4`(경량) · `solar-pro3` · `solar-pro2` |
| 문서 | https://console.upstage.ai/docs |

- OpenAI SDK 호환. `temperature`·`presence_penalty`·`frequency_penalty`를 그대로 받습니다(sarangbang 기본값 사용).
- 추론 모드가 있는 모델에서 응답이 비거나 느리면 요청에 `reasoning_effort`를 줍니다.
  `get_provider("upstage").lane("base", extra={"reasoning_effort": "none"})` 또는 CLI `--extra '{"reasoning_effort":"none"}'`.
- 오픈 웨이트 판(Solar Open 100B · Solar Open2 250B)은 아래 "직접 띄우기"를 보세요.

```bash
export UPSTAGE_API_KEY=...
sarangbang doctor --provider upstage
sarangbang quickstart --provider upstage --model solar-mini4 --msgs 20
```

### 네이버클라우드 CLOVA Studio (HyperCLOVA X) — `clova`

| 항목 | 값 |
|---|---|
| 주소 | `https://clovastudio.stream.ntruss.com/v1/openai` (OpenAI 호환 엔드포인트) |
| 키 | CLOVA Studio [API 키] 메뉴의 테스트·서비스 키 → `CLOVASTUDIO_API_KEY` |
| 모델 | `HCX-005`(멀티모달, 128K) · `HCX-DASH-002`(경량, 32K) · `HCX-007`(하이브리드 추론, 128K) |
| 문서 | https://api.ncloud-docs.com/docs/clovastudio-openaicompatibility |

- **`presence_penalty`·`frequency_penalty`를 받지 않습니다.** 프리셋은 두 인자를 빼고 `temperature`만 보냅니다.
  반복을 줄이려면 CLOVA 전용 인자 `repetition_penalty`를 `extra`로 줍니다: `lane(extra={"repetition_penalty": 1.1})`.
- `HCX-007`은 추론 모델입니다. 단톡방 발화에는 `extra={"reasoning_effort": "none"}`을 권합니다(`HCX-005`·`HCX-DASH-002`에는 주지 않음).
- `n`은 1만, `response_format`은 `json_schema`만 받습니다. sarangbang의 `JsonLLM`은 응답 본문에서 JSON 객체를 찾아 쓰므로 그대로 동작합니다.
- 오픈 웨이트 판(HyperCLOVA X SEED Think 14B·32B)은 아래 "직접 띄우기"를 보세요.

```bash
export CLOVASTUDIO_API_KEY=...
sarangbang doctor --provider clova --model HCX-DASH-002
```

### SK텔레콤 A.X · LG AI연구원 EXAONE · 카카오 Kanana · KT 믿:음

2026년 10월 기준으로 **개발자용 공개 API를 직접 운영하지는 않습니다.** 세 회사 모두 Hugging Face에 오픈 웨이트를 공개하므로 아래
"직접 띄우기"로 쓰거나, 중개 플랫폼에 올라와 있을 때 그쪽 키로 씁니다. (LG AI연구원은 EXAONE 4.0·K-EXAONE을 FriendliAI를 통해 API로
제공해 왔고, SKT는 A.X K1을 공모전·스타트업 프로그램에 API로 제공했습니다. 기업용 온프레미스 계약은 각 사에 문의.)

## 2. 중개 플랫폼에 올라온 국산 모델

### FriendliAI — `friendli`

| 항목 | 값 |
|---|---|
| 주소 | `https://api.friendli.ai/serverless/v1` (Model APIs) · Dedicated Endpoints는 `https://api.friendli.ai/dedicated/v1` |
| 키 | https://friendli.ai → Personal Access Token → `FRIENDLI_TOKEN` |
| 모델 | 바뀝니다 — `GET /models`로 확인. EXAONE 4.0(2025-07)과 K-EXAONE 236B(2025-12~2026-01 무료)를 서빙해 온 플랫폼 |
| 문서 | https://friendli.ai/docs/guides/openai-compatibility |

국산 모델이 Model APIs 목록에 없을 때는 Dedicated Endpoint로 Hugging Face의 임의 모델(예: `LGAI-EXAONE/EXAONE-4.5-33B`)을 올려 쓸 수
있습니다. 이때 주소는 dedicated 쪽, 모델 이름은 엔드포인트 id입니다: `get_provider("friendli").lane(base_url="https://api.friendli.ai/dedicated/v1", model="<endpoint-id>")`.

### OpenRouter — `openrouter`

| 항목 | 값 |
|---|---|
| 주소 | `https://openrouter.ai/api/v1` |
| 키 | https://openrouter.ai/keys → `OPENROUTER_API_KEY` |
| 모델 | `upstage/solar-pro4` · `upstage/solar-mini4` · `upstage/solar-pro-3` (2026-10 기준 국산 모델은 Solar 계열) |
| 문서 | https://openrouter.ai/models?q=upstage |

OpenRouter는 앱 식별 헤더를 권장합니다: `lane(headers={"HTTP-Referer": "https://github.com/SpringWindsTeam/sarangbang", "X-Title": "sarangbang"})`.

### Hugging Face Inference Providers

`https://router.huggingface.co/v1`(OpenAI 호환)도 같은 방식으로 붙일 수 있지만 2026년 10월 기준 국산 모델은 목록에 없었습니다.
올라오면 `--base-url https://router.huggingface.co/v1 --api-key-env HF_TOKEN --model <id>`로 씁니다.

## 3. 오픈 웨이트를 직접 띄우기

가장 많은 선택지가 있는 경로입니다. vLLM(`http://localhost:8000/v1`)·SGLang(`:30000`)·Ollama(`:11434`)·LM Studio(`:1234`)가 모두
OpenAI 호환 서버를 띄워 주고, sarangbang 프리셋은 키 없이(`EMPTY`) 붙습니다.

### 노트북에서 5분 — Ollama + EXAONE 3.5

```bash
ollama pull exaone3.5:7.8b                 # 2.4B 판은 exaone3.5:2.4b
sarangbang doctor --provider ollama --model exaone3.5:7.8b
sarangbang quickstart --provider ollama --model exaone3.5:7.8b --msgs 20
```

### GPU 서버 — vLLM

```bash
pip install -U vllm
vllm serve skt/A.X-4.0-Light --port 8000                      # 7B · GPU 한 장
# vllm serve LGAI-EXAONE/EXAONE-4.5-33B --tensor-parallel-size 2 --reasoning-parser qwen3 --max-model-len 65536
sarangbang doctor --provider vllm --model skt/A.X-4.0-Light
sarangbang run examples/cafe_price.json --provider vllm --model skt/A.X-4.0-Light --slots 8 --msgs 60 --out run.json
```

두 레인(큰 모델은 앵커, 빠른 모델은 기본)을 쓰려면 서버를 둘 띄우고 `--anchor-provider vllm --anchor-model <큰 모델>`에
`SARANGBANG_ANCHOR_BASE_URL`로 두 번째 서버 주소를 줍니다.

### 추론(생각) 모드 끄기

최근 국산 모델 대부분이 추론 모드를 가지고 있습니다. 단톡방 발화는 한두 문장이고 `max_tokens=400`이므로 **생각을 켠 채 두면 응답이
비거나 잘립니다.** 끄는 법은 모델마다 다르고, `sarangbang models`의 "추론 끄기" 칸에 적혀 있습니다.

| 모델 계열 | 끄는 법 | sarangbang에서 |
|---|---|---|
| EXAONE 4.x · K-EXAONE · A.X K1/K2 | `chat_template_kwargs: {"enable_thinking": false}` | `vllm`·`sglang` 프리셋 기본값 |
| Solar Open · Solar Open2 | `reasoning_effort: "none"` | `lane(extra={"reasoning_effort": "none"})` |
| HyperCLOVA X SEED Think | `chat_template_kwargs: {"force_reasoning": false}` | `lane(sampling={..., "chat_template_kwargs": {"force_reasoning": False}})` |
| Kanana 2 (-instruct) · Mi:dm 2.0 · A.X 4.0 | 추론 모드 없음 | 그대로 |

응답에 `<think>…</think>`가 섞여 와도 `clean_reply`가 떼어 내지만, 생각에 토큰을 다 쓰면 본문이 없습니다. `sarangbang doctor`가
응답이 비면 경고합니다.

### 모델 목록 (2026-10)

라이선스 요약은 참고용입니다. **사용 전 모델 카드의 라이선스 전문을 읽으세요.** 특히 EXAONE(비상업)·Kanana(API 제공·재판매 별도 계약)·
Solar(표기 의무)·HyperCLOVA X SEED는 조건이 있습니다.

| 모델 | 제공 | 크기 | 라이선스 | 상업 이용 | 메모 |
|---|---|---|---|---|---|
| `LGAI-EXAONE/EXAONE-4.5-33B` | LG AI연구원 | 33B | EXAONE AI Model License 1.2-NC | 비상업 | 2026-04. 비전 포함. `--reasoning-parser qwen3` |
| `LGAI-EXAONE/K-EXAONE-236B-A23B` | LG AI연구원 | 236B-A23B | K-EXAONE License | 조건부 | 독파모 1차 모델. vllm≥0.14 |
| `LGAI-EXAONE/K-EXAONE-2.0-750B-A37B` | LG AI연구원 | 750B-A37B | Apache-2.0 | 가능 | 독파모 2차 모델(2026-08). FP8·NVFP4 판 |
| `LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct` | LG AI연구원 | 7.8B | EXAONE License | 비상업 | 노트북용. Ollama `exaone3.5` |
| `skt/A.X-K2` | SK텔레콤 | 688B MoE | Apache-2.0 | 가능 | 독파모 2차 모델(2026-07). `--reasoning-parser deepseek_v3` |
| `skt/A.X-K1` | SK텔레콤 | 519B-A33B | Apache-2.0 | 가능 | 독파모 1차 모델(2026-01) |
| `skt/A.X-4.0` | SK텔레콤 | 72B | Qwen License | 조건부 | sarangbang 기본 프롬프트를 맞춘 모델 중 하나 |
| `skt/A.X-4.0-Light` | SK텔레콤 | 7B | Apache-2.0 | 가능 | GPU 한 장. 빠른 레인용 |
| `upstage/Solar-Open2-250B` | 업스테이지 | 250B-A15B | Upstage Solar License | 조건부 | 독파모 2차 모델. "Built with Solar" 표기 |
| `upstage/Solar-Open-100B` | 업스테이지 | 102B-A12B | Upstage Solar License | 조건부 | 독파모 1차 모델(2026-01) |
| `naver-hyperclovax/HyperCLOVAX-SEED-Think-32B` | 네이버클라우드 | 33B | HyperCLOVA X SEED License | 조건부 | 추론 필드 분리는 hcx-vllm-plugin |
| `naver-hyperclovax/HyperCLOVAX-SEED-Think-14B` | 네이버클라우드 | 14B | HyperCLOVA X SEED License | 조건부 | GPU 한 장 |
| `kakaocorp/kanana-2-30b-a3b-instruct` | 카카오 | 30B-A3B | Kanana License | 조건부 | API·클라우드 제공·MAU 1천만↑ 별도 계약 |
| `kakaocorp/kanana-2-3b-instruct` | 카카오 | 3.5B | Kanana Open License | 조건부 | 작은 GPU·CPU |
| `K-intelligence/Midm-2.0-Base-Instruct` | KT | 11.5B | MIT | 가능 | 믿:음 2.0. Mini 2.3B 판 |
| `trillionlabs/Tri-21B-Think` | 트릴리온랩스 | 21B | Apache-2.0 | 가능 | 비추론 판 Tri-21B는 접근 신청 |
| `Motif-Technologies/Motif-3` | 모티프테크놀로지스 | 315B MoE | MIT | 가능 | 독파모 2차 참가. `--reasoning-parser motif` |
| `NCSOFT/Llama-VARCO-8B-Instruct` | NC AI | 8B | Llama 3.1 Community | 조건부 | 2024-12 |

sarangbang의 기본 프롬프트와 후처리는 **EXAONE과 A.X**의 한국어 응답을 기준으로 맞췄습니다(README "EXAONE과 A.X에 맞춘 설정").
다른 모델은 `sarangbang run … --out run.json`으로 몇 번 돌려 `calls[].fixes`(응답 정리 내역)와 대화를 보고 사양을 맞추는 것이 좋습니다.

## 4. 정책 배경: 독자 AI 파운데이션 모델 프로젝트

과학기술정보통신부의 "독자 AI 파운데이션 모델" 프로젝트(2025-08 시작)는 국산 파운데이션 모델을 단계 평가로 선발합니다. 위 표의 K-EXAONE,
A.X K1/K2, Solar Open/Open2, Motif 3이 이 프로젝트에서 공개된 모델입니다.

- 1차 평가(2026-01-15): LG AI연구원·SK텔레콤·업스테이지 진출, 네이버클라우드·NC AI 탈락. 이후 패자부활전으로 모티프테크놀로지스 합류.
- 2차 평가(2026-08-18): 업스테이지(Solar Open2)·SK텔레콤(A.X K2)·LG AI연구원(K-EXAONE 2.0) 진출, 모티프(Motif 3) 탈락.
- 3차 평가는 2026년 하반기 진행, 최종 결과는 2027년 초 예정. 2027년부터는 지원 체계가 재편될 수 있다고 정부가 밝혔습니다.

프로젝트 밖에서도 네이버(HyperCLOVA X · SEED), 카카오(Kanana), KT(믿:음), 트릴리온랩스(Tri) 등이 모델을 계속 공개하고 있습니다.
여론 시뮬레이션처럼 한국어 구어체·지역·세대 표현이 중요한 작업에서는 모델별 차이가 커서, 같은 시나리오를 두세 모델로 돌려 비교해 보기를 권합니다.

## 5. 비용 감각

- 방 하나(시민 30명, 메시지 100개)는 호출 100~150번, 호출당 입력 1.5~3K 토큰·출력 50~100 토큰 정도입니다.
  호스팅 API의 경량 모델(예: solar-mini4, HCX-DASH-002)이면 방 하나에 수십 원~수백 원 수준입니다.
- 직접 띄우면 7B급은 GPU 한 장(24GB)으로 `--slots 8` 정도 동시 호출이 무난합니다. MoE 대형 모델(A.X K2, K-EXAONE 2.0)은 다중 GPU 노드가 필요합니다.
- 비용 없이 흐름만 보려면 `--fake`, 노트북에서 실제 모델을 보려면 Ollama + EXAONE 3.5 2.4B.

## 6. 자주 겪는 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| `400 … unknown parameter chat_template_kwargs` | 호스팅 API에 vLLM 전용 인자를 보냄 | 프리셋(`--provider`)을 쓰거나 `lane(sampling={"temperature": 0.7})` |
| `400 … presence_penalty` | CLOVA Studio는 미지원 | `clova` 프리셋 사용 |
| 응답이 비어 있고 `calls[].raw`가 `<think>`로 시작 | 추론 모드 켜짐 | 위 "추론 모드 끄기" |
| `401`/`403` | 키 환경 변수 이름이 다름 | `sarangbang providers`에서 키 변수 확인(✓ 표시) |
| `429`가 잦음 | 동시 호출 한도 초과 | `--slots`를 줄인다. sarangbang은 429·5xx를 4·8·12…초 간격으로 6번 재시도 |
| 모델이 대화 기록을 통째로 베껴 씀 | 작은 모델·영어 중심 모델 | `calls[].fixes`에 "옮겨 적은 기록 줄"이 많으면 모델을 바꾸거나 사양 문구를 조정 |
