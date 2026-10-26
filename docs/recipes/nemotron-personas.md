# 공개 데이터셋으로 시민 뽑기

[Nemotron-Personas-Korea 증강판](https://huggingface.co/datasets/springwindteam/nemotron-personas-korea-augmented)(한국인 100만 명, 19세 이상, CC BY 4.0)에서 시민을 읽어 방을 만듭니다. 시민 정보를 직접 지어내지 않고 인구 분포를 따르는 데이터에서 가져오는 방법입니다.

## 코드

```python
import asyncio

from sarangbang import GENERIC_KO, Room, build_room, load_spec, run_rooms
from sarangbang.adapters import NemotronKoreaAdapter, load_nemotron_rows
from sarangbang.scenario import fake_lane

rows = load_nemotron_rows(12, 0, "서울")              # n명, 건너뛸 행 수, 시·도 (데이터셋 뷰어 API, 100행씩)
ad = NemotronKoreaAdapter()
target = {"relations": [                               # 데이터 열 조건 → 소식과의 관계 문장·점수
    {"if": {"housing_type": ["다세대주택", "연립주택", "단독주택"]}, "text": "주차 공간이 부족한 집에 산다", "score": 2},
    {"if": {"has_children": True}, "text": "아이들을 태우고 다닐 일이 많다", "score": 1},
]}
digest = {"summary": "구청이 다음 달부터 공영주차장 요금을 올린다.",
          "facts": [{"statement": "다음 달 1일부터 공영주차장 요금이 30분 500원에서 800원으로 오른다", "status": "확정·시행"}]}

names = ad.display_names(rows)
prompts = build_room(rows, names, adapter=ad, digest=digest, target=target, given=[[] for _ in rows], cards_by={},
                     leans=[None] * len(rows), spec=load_spec("ko_generic"), topic=GENERIC_KO)
sharer = max(range(len(rows)), key=lambda i: (ad.static_score(rows[i], target), -i))
room = Room("r1", rows, names, prompts, target, {"author": sharer, "text": "공영주차장 요금 오른대요"},
            target_msgs=10, scorer=ad.static_score)
asyncio.run(run_rooms([room], {"base": fake_lane()}))
for m in room.msgs:
    print(names[m["author"]], m["text"])
```

실제 모델로 돌리는 전체 예는 [`examples/nemotron_korea.py`](../../examples/nemotron_korea.py)에 있습니다.

## 알아 둘 점

- 데이터셋에는 성격, 자녀 나이, 쓰는 제품, 콘텐츠 소비 습관이 없습니다. 이런 정보가 중요한 주제라면 다른 데이터를 붙이거나 자기 어댑터를 만듭니다([04. 시민 구성하기](../knowledge-base/04-personas.md)).
- 이 예제는 카드 없이 돌립니다. 카드가 없으면 같은 화제로 모이는 경우가 많았으니, 실제로 쓸 때는 쟁점 카드를 함께 넣습니다([03. 쟁점 카드 만들기](../knowledge-base/03-cards.md)).
- 데이터셋을 쓸 때는 소개 페이지의 인용 안내에 따라 원본과 증강판을 함께 표기합니다.
