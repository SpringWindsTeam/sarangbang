# 시나리오 파일로 실행하기

주제 정보·시민·카드를 JSON 한 파일(시나리오 파일)에 담아 방 하나를 돌립니다. 형식은 [`src/sarangbang/scenario.py`](../../src/sarangbang/scenario.py) 첫머리에 있고, [`examples/cafe_price.json`](../../examples/cafe_price.json)이 본보기입니다.

## 명령줄로

```bash
sarangbang run examples/cafe_price.json --fake --msgs 10                 # 모델 없이 흐름만
sarangbang run examples/cafe_price.json --provider friendli --model <모델> --msgs 30 --out cafe_run.json
```

`--out`을 주면 메시지와 호출 기록이 JSON으로 저장됩니다.

## 라이브러리로

```python
import asyncio
import json

from sarangbang import run_rooms
from sarangbang import scenario as S

d = S.load_scenario("examples/cafe_price.json")
prep = S.prepare(d)                                    # 카드 배분 → 시민별 프롬프트 (LLM 호출 없음)
share = S.seed_share(d, prep, None)                    # 첫 메시지: 시나리오의 share → 없으면 고정 문장
room = S.make_room(d, prep, share, target_msgs=10)

stats = asyncio.run(run_rooms([room], {"base": S.fake_lane()},
                              on_message=lambda r, m: print(S.format_line(r, m))))
json.dump(S.transcript(d, room, stats), open("cafe_run.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
```

실제 모델로 바꾸려면 `S.fake_lane()` 대신 `lane_from_env("base")`를, 첫 메시지를 LLM으로 쓰려면 `S.seed_share(d, prep, json_llm_from_env())`를 씁니다(둘 다 `from sarangbang import …`). 환경 변수는 [국산 AI 모델 사용 가이드](../korean-ai-providers.md)를 보세요.

## 다음 단계

- 시나리오 내용을 직접 채우는 방법: [지식 베이스 만들기](../knowledge-base)
- 파일을 나눠 작성·점검한 뒤 시나리오로 내보내기: `python -m kb_tools.export` ([지식 베이스 만들기 — 도구](../knowledge-base/README.md#도구))
