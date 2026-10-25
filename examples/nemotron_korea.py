"""Nemotron-Personas-Korea(증강판) 시민으로 방 하나 돌리기 — 시나리오 JSON 없이 코드로 주제를 만든다.

    SARANGBANG_PROVIDER=vllm SARANGBANG_MODEL=skt/A.X-4.0-Light python examples/nemotron_korea.py --n 30 --msgs 30
    SARANGBANG_PROVIDER=upstage UPSTAGE_API_KEY=… python examples/nemotron_korea.py --province 서울

데이터셋(CC BY 4.0): https://huggingface.co/datasets/springwindteam/nemotron-personas-korea-augmented
`load_nemotron_rows`는 Hugging Face 데이터셋 뷰어 API(/rows, 한 번에 100행)로 --skip 위치부터 n명을 읽는다(1.2GB를 내려받지 않는다).
표본 위치를 바꾸려면 --skip을 바꾼다. 대규모 표집은 parquet을 내려받아 pandas·polars로 고르는 편이 낫다.
"""
from __future__ import annotations

import argparse
import asyncio

from sarangbang import GENERIC_KO, Room, build_room, json_llm_from_env, lane_from_env, load_spec, run_rooms
from sarangbang import material as M
from sarangbang.adapters import NemotronKoreaAdapter, load_nemotron_rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--province", default=None, help="예: 서울")
    ap.add_argument("--msgs", type=int, default=30)
    a = ap.parse_args()

    rows = load_nemotron_rows(a.n, a.skip, a.province)
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
    share = M.seed_message(json_llm_from_env(), title, digest, ad.seed_profile(rows[sharer], target), topic=topic)
    room = Room("r1", rows, names, prompts, target, {"author": sharer, "text": share}, target_msgs=a.msgs,
                scorer=ad.static_score, topic=topic)
    asyncio.run(run_rooms([room], {"base": lane_from_env("base")}))
    for m in room.msgs:
        rep = f"(#{m['reply_to']}에 답장) " if m.get("reply_to") else ""
        print(f"#{m['id']:>3} {names[m['author']]}: {rep}{m['text']}")


if __name__ == "__main__":
    main()
