# 기여하기

sarangbang에 관심을 가져 주셔서 고맙습니다. 버그 보고, 국산 모델 제공처 정보 갱신, 새 어댑터, 사양 문구 실험 모두 환영합니다.

## 개발 환경

```bash
git clone https://github.com/SpringWindsTeam/sarangbang.git
cd sarangbang
python -m venv .venv && source .venv/bin/activate     # 또는 uv venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                 # 시험(네트워크 없음)
ruff check .              # 린트
sarangbang quickstart --fake
```

## 원칙

- **엔진에 무작위를 넣지 않는다.** 발언 순위·카드 배분·방 진행은 같은 입력이면 같은 결과여야 한다.
  결과가 달라지는 곳은 모델 표본 추출뿐이다.
- **매 호출은 독립이다.** 모델 쪽 기억·대화 누적을 들이지 않는다. 대화 상태는 `Room.msgs`가 들고 있다.
- **시민 레코드 모양을 엔진에 넣지 않는다.** 레코드를 읽는 일은 `PersonaAdapter`가 한다.
- **런타임 의존성은 `httpx` 하나.** 새 의존성은 optional extra로 분리한다.
- **비밀값·실데이터를 커밋하지 않는다.** API 키, 내부 주소, 실제 사람의 글·닉네임·페르소나 원자료는 저장소에 두지 않는다.
  예제 데이터는 지어낸 장난감 데이터나 합성 데이터만 쓴다.

## 이런 기여가 특히 반갑습니다

| 종류 | 어디를 고치나 |
|---|---|
| 국산 모델 제공처 정보(주소·모델 이름·지원 인자)가 바뀌었다 | `src/sarangbang/providers.py`, `docs/korean-ai-providers.md` |
| 새 공개 페르소나 데이터셋 어댑터 | `src/sarangbang/adapters/` + 시험용 합성 표본 몇 행 |
| 새 모델에서 응답 형식 오류를 봤다 | `src/sarangbang/reply.py`(`clean_reply`) + `tests/test_reply.py`에 사례 추가 |
| 사양 문구(프롬프트) 개선 | 아래 "사양 문구를 바꾸는 제안" |

## 사양 문구를 바꾸는 제안

기본 사양 `ko_s12`·`ko_generic`의 문구 하나가 화제 수렴·지어냄·남의 말 옮김을 크게 바꿉니다. 문구 변경 PR에는 다음을 함께 적어 주세요
(이슈 템플릿 "사양 문구 변경 제안"을 쓰면 됩니다).

1. 비교 조건 — 주제, 시민 수, 메시지 수, 모델(제공처·버전), 반복 횟수
2. 판정 기준 — 무엇을 어떻게 셌는지(예: 고른 화제 수, 지어낸 신상 비율, 같은 문장 반복)
3. 결과 — 바꾸기 전과 후의 수치, 대화 표본

새 문구를 기본값으로 바꾸기보다 새 사양 파일(`specs/<이름>.json`)로 추가하는 것을 먼저 고려해 주세요.

## 커밋·PR

- 브랜치는 `main`에서 따고, PR은 `main`으로 보냅니다. CI(시험·린트·빌드)가 통과해야 합니다.
- 커밋 메시지는 한국어나 영어 모두 좋습니다. 무엇을 왜 바꿨는지 적어 주세요.
- 동작이 바뀌면 시험을 함께 고치거나 추가하고, 사용자에게 보이는 변화는 `CHANGELOG.md`의 "미공개" 항목에 한 줄 적어 주세요.
- 라이선스: 기여한 코드는 저장소와 같은 [Apache License 2.0](LICENSE)으로 배포되는 데 동의한 것으로 봅니다.

## 배포(유지 관리자용)

버전 올리기 → 태그 → PyPI·GitHub Release 절차는 [docs/release.md](docs/release.md)에 있습니다.
