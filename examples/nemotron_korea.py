"""Nemotron-Personas-Korea(증강판) 시민으로 방 하나 돌리기.

    SARANGBANG_BASE_URL=… SARANGBANG_API_KEY=… SARANGBANG_MODEL=… python examples/nemotron_korea.py --n 30 --msgs 30

데이터셋(CC BY 4.0): https://huggingface.co/datasets/springwindteam/nemotron-personas-korea-augmented
Hugging Face 데이터셋 뷰어 API(/rows, 한 번에 100행)로 --skip 위치부터 n명을 읽는다(전체 1.2GB를 내려받지 않는다).
표본 위치를 바꾸려면 --skip을 바꾼다. 대규모 표집은 parquet을 내려받아 pandas·polars로 고르는 편이 낫다.
"""
from __future__ import annotations

import argparse
import asyncio
import os

from sarangbang import GENERIC_KO, JsonLLM, Lane, Room, build_room, load_spec, run_rooms
from sarangbang import material as M
from sarangbang.adapters import NemotronKoreaAdapter

DATASET = "springwindteam/nemotron-personas-korea-augmented"


def load_rows(n: int, skip: int = 0, province: str | None = None) -> list[dict]:
    import httpx

    out: list[dict] = []
    off = skip
    with httpx.Client(timeout=60) as c:
        while len(out) < n:
            r = c.get("https://datasets-server.huggingface.co/rows",
                      params={"dataset": DATASET, "config": "default", "split": "train", "offset": off, "length": 100})
            r.raise_for_status()
            rows = [x["row"] for x in r.json().get("rows") or []]
            if not rows:
                break
            out += [x for x in rows if not province or x.get("province") == province]
            off += len(rows)
    return out[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--province", default=None, help="예: 서울")
    ap.add_argument("--msgs", type=int, default=30)
    a = ap.parse_args()
    base, key, model = os.environ["SARANGBANG_BASE_URL"], os.environ["SARANGBANG_API_KEY"], os.environ["SARANGBANG_MODEL"]

    rows = load_rows(a.n, a.skip, a.province)
    title = "동네 공영주차장 요금 인상"
    digest = {"summary": "구청이 다음 달부터 공영주차장 요금을 올린다. 거주자 우선주차는 그대로다.",
              "facts": [{"statement": "다음 달 1일부터 공영주차장 요금이 30분 500원에서 800원으로 오른다", "status": "확정·시행"},
                        {"statement": "거주자 우선주차 요금은 월 3만 원으로 그대로다", "status": "확정·시행"},
                        {"statement": "늘어난 수입은 주차장 보수와 CCTV 설치에 쓴다고 했다", "status": "계획·목표"}]}
    target = {"relations": [
        {"if": {"housing_type": ["다세대주택", "연립주택", "단독주택"]}, "text": "주차 공간이 부족한 집에 산다", "score": 2},
        {"if": {"has_children": True}, "text": "아이들을 태우고 다닐 일이 많다", "score": 1},
    ]}
    ad, topic = NemotronKoreaAdapter(), GENERIC_KO
    names = ad.display_names(rows)
    prompts = build_room(rows, names, adapter=ad, digest=digest, target=target, given=[[] for _ in rows], cards_by={},
                         leans=[None] * len(rows), spec=load_spec("ko_generic"), topic=topic)
    sharer = max(range(len(rows)), key=lambda i: (ad.static_score(rows[i], target), -i))
    share = M.seed_message(JsonLLM.openai(base, key, model), title, digest, ad.seed_profile(rows[sharer], target), topic=topic)
    room = Room("r1", rows, names, prompts, target, {"author": sharer, "text": share}, target_msgs=a.msgs,
                scorer=ad.static_score, topic=topic)
    asyncio.run(run_rooms([room], {"base": Lane.openai("base", base, key, model, slots=2)}))
    for m in room.msgs:
        rep = f"(#{m['reply_to']}에 답장) " if m.get("reply_to") else ""
        print(f"#{m['id']:>3} {names[m['author']]}: {rep}{m['text']}")


if __name__ == "__main__":
    main()
