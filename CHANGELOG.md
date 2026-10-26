# 변경 기록

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르고, 버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

## 미공개

### 추가

- **지식 베이스 문서**(`docs/knowledge-base/`): 주제 정보·쟁점 카드·시민·주제 문구를 어떻게 구성해야 대화가 잘 나오는지 — 원칙, 도메인별 대응표, 점검 목록, 자주 생기는 문제와 대응.
- **예시 지식 베이스 7개**(`examples/knowledge-bases/`, 모두 가상 데이터)와 도구(`examples/kb_tools/`: validate · extract_digest · make_cards · run · export). `export`는 시나리오 파일로 내보내 `sarangbang run`으로 돌릴 수 있게 한다.
- **실행 예제**(`docs/recipes/`): 시나리오 파일, 연애 예능 시청자 단톡방, Nemotron 시민, 모델 두 개, 플러그인.
- README 머리에 데모 GIF(`assets/demo-chat.gif`).

## 0.2.0 — 2026-10-25

첫 PyPI 배포 준비판. `pip install sarangbang` 뒤 `sarangbang quickstart --fake`로 바로 돌려 볼 수 있습니다.

### 추가

- **`sarangbang` 명령**(`cli.py`): `quickstart`(내장 시나리오) · `run <시나리오.json>`(결과 JSON 저장) · `providers`(국산 AI를 쓸 수 있는 곳) ·
  `models`(오픈 웨이트 국산 모델 목록과 vllm serve 힌트) · `doctor`(키·주소·모델 연결 점검).
- **제공처 프리셋**(`providers.py`): `get_provider("upstage"|"clova"|"friendli"|"openrouter"|"vllm"|"sglang"|"ollama"|"lmstudio").lane(...)` —
  주소·키 환경 변수·추천 모델·그 서버가 받는 표본 추출 인자(CLOVA Studio는 presence/frequency_penalty 제외, 로컬 서버는 생각 끄기)를 담는다.
  `lane_from_env()`·`json_llm_from_env()`는 `SARANGBANG_PROVIDER` 또는 `SARANGBANG_BASE_URL`·`SARANGBANG_API_KEY`·`SARANGBANG_MODEL`로 레인을 만든다.
  `OPEN_MODELS`: EXAONE·K-EXAONE·A.X·Solar Open·HyperCLOVA X SEED·Kanana·Mi:dm 등 18개 모델의 크기·라이선스·추론 모드 끄는 법.
- **시나리오 파일**(`scenario.py`): 주제·시민·카드를 JSON 하나에 담아 `load_scenario` → `prepare` → `make_room`으로 방을 만든다.
  내장 시나리오 `toy_library`는 패키지 데이터(`sarangbang/data/`)로 들어가 설치만으로 쓸 수 있다. 예제 `examples/cafe_price.json` 추가.
- `sarangbang.adapters.load_nemotron_rows`: Nemotron-Personas-Korea 증강판을 데이터셋 뷰어 API로 n행만 읽는다(예제에서 패키지로 옮김).
- `Lane`·`JsonLLM`에 `headers` 필드(중개 플랫폼용 추가 헤더). `LLMError`를 패키지에서 내보낸다.
- 문서: README를 PyPI 설치·CLI 중심으로 고치고 **국산 AI 모델 사용 가이드** 절과 [docs/korean-ai-providers.md](docs/korean-ai-providers.md)
  (호스팅 API·중개 플랫폼·직접 띄우기·모델별 라이선스·독자 AI 파운데이션 모델 현황)를 추가. 영어 README(`README.en.md`) 분리.
- 저장소 체계: GitHub Actions CI(Python 3.10–3.14 시험·린트·빌드·휠 설치 점검), 태그 기반 릴리스(PyPI Trusted Publishing + GitHub Release),
  이슈·PR 템플릿, Dependabot, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, `py.typed`.

### 변경

- `examples/toy_policy.json` → `src/sarangbang/data/toy_library.json`(패키지 데이터). 예제 스크립트는 새 API를 쓰도록 고침.
- `pyproject.toml`: 버전을 `__init__.py`에서 읽고(`dynamic`), 분류자·URL·`[project.scripts]` 추가.

## 0.1.0 — 2026-10

- 첫 공개. 민심(minsim) 교육정책 시뮬레이션의 단톡방 엔진을 독립 패키지로 분리.
- 엔진(`Room`, `run_rooms`), OpenAI 호환 레인(`Lane`, `JsonLLM`), 사양 렌더(`build_room`, 기본 사양 `ko_s12`),
  대화 기록·응답 정리, 쟁점 카드 배분, 카드 관련성·연결 의견·첫 메시지 프롬프트, `PersonaAdapter`·`DictAdapter`.
- 주제 어댑터 `Topic`(입장 문장·관계 항목 이름·준비 프롬프트·주제 일반어) — `POLICY_KO`(교육정책 테스트 문구), `GENERIC_KO`(범용, 기본값).
- 범용 설정 `ko_generic`(기본값) 추가. `ko_s12`는 `POLICY_KO`와 짝.
- 프롬프트 주입 인터페이스 `PromptPlugin`(system_sections · tail · call_context)과 `StaticSections`.
- `NemotronKoreaAdapter`(Nemotron-Personas-Korea 증강판 행 그대로), 예제 `nemotron_korea.py`.
