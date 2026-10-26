# 프롬프트에 칸 추가하기

프롬프트 사양을 고치지 않고 시민 프롬프트에 정보를 더할 때 플러그인을 씁니다. 모든 시민에게 같은 칸을 붙이거나, 대화가 진행되는 날짜에 따라 상황을 알려 줄 수 있습니다.

## 코드

```python
import asyncio

from sarangbang import StaticSections, run_rooms
from sarangbang import scenario as S


class Weather:
    """둘째 날 호출에만 '비가 온다'를 붙인다(대화 진행에 따라 바뀌는 정보)."""

    def call_context(self, room, i):
        return "(오늘은 비가 온다)" if room.vt(room.n_say())["day"] == 2 else ""


d = S.load_scenario("examples/cafe_price.json")
d["days"] = 2
common = StaticSections(["[공통] 이 단톡방에서는 서로 존댓말을 쓴다"])
prep = S.prepare(d, plugins=[common])                  # 시스템 프롬프트에 붙는 칸 — 방을 만들 때 한 번
room = S.make_room(d, prep, S.seed_share(d, prep, None), target_msgs=12, plugins=[Weather()])   # 호출마다 붙는 문맥
asyncio.run(run_rooms([room], {"base": S.fake_lane()}))
print(prep.prompts[0].system)
```

## 붙는 위치

| 메서드 | 실행 시점 | 붙는 곳 |
|---|---|---|
| `system_sections(p, i, ctx)` | 방을 만들 때 한 번 | 시스템 프롬프트의 사실 칸 뒤 |
| `tail(p, i, ctx)` | 방을 만들 때 한 번 | 응답 직전 안내 끝 |
| `call_context(room, i)` | 모델을 부를 때마다 | 대화 기록과 응답 직전 안내 사이 |

## 쓰기 전에

플러그인은 지시를 붙이기 쉬운 도구라서, 같은 내용을 지식 베이스 칸(사실·카드·시민)으로 줄 수 있는지 먼저 봅니다. 지시보다 재료가 잘 듣는 이유는 [01. 지식 베이스 구성 방법 — 원칙 3](../knowledge-base/01-knowledge-base.md#3-지시보다-재료를-준다)에 있습니다.
