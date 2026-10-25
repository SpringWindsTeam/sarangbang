# 예제

| 파일 | 내용 |
|---|---|
| [`quickstart.py`](quickstart.py) | 내장 시나리오(`toy_library`)를 라이브러리 API로 돌린다. `--fake`면 네트워크 없이. |
| [`nemotron_korea.py`](nemotron_korea.py) | Nemotron-Personas-Korea 증강판 행을 `load_nemotron_rows`로 읽어 코드로 주제를 만든다. |
| [`cafe_price.json`](cafe_price.json) | 직접 만든 시나리오 파일 본보기 — `sarangbang run examples/cafe_price.json --fake` |

시나리오 JSON의 형식은 [`src/sarangbang/scenario.py`](../src/sarangbang/scenario.py) 첫머리와
내장 시나리오 [`toy_library.json`](../src/sarangbang/data/toy_library.json)을 참고하세요.
모델 연결은 `sarangbang providers`(국산 AI를 쓸 수 있는 곳)와 [docs/korean-ai-providers.md](../docs/korean-ai-providers.md)를 보세요.
