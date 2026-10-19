"""sarangbang 빠른 시작 — 장난감 정책 하나·시민 4명·카드 4장으로 방 하나를 돌린다.

    python examples/quickstart.py --fake            # 네트워크 없이(정해 둔 답으로) 흐름만 확인
    python examples/quickstart.py --fake --topic policy   # 정책 주제 문구(ko_s12)로
    SARANGBANG_BASE_URL=https://…/v1 SARANGBANG_API_KEY=… SARANGBANG_MODEL=… python examples/quickstart.py

실제 모델이면 첫 메시지도 LLM(material.seed_message)이 쓴다. --fake면 고정 문장.
"""
from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import os
from pathlib import Path

from sarangbang import (
    GENERIC_KO,
    POLICY_KO,
    DictAdapter,
    FakeLane,
    JsonLLM,
    Lane,
    Room,
    allocate,
    build_room,
    hearsay_fill,
    kept,
    load_spec,
    run_rooms,
)
from sarangbang import material as M

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--msgs", type=int, default=20)
    ap.add_argument("--topic", choices=["generic", "policy"], default="generic", help="주제 문구: 범용 소식 | 정책(ko_s12)")
    a = ap.parse_args()
    d = json.loads((HERE / "toy_policy.json").read_text(encoding="utf-8"))
    topic, spec = (POLICY_KO, load_spec("ko_s12")) if a.topic == "policy" else (GENERIC_KO, load_spec("ko_generic"))
    ad = DictAdapter()
    ps, cards, rel = d["personas"], d["cards"], d["relevance"]
    names = ad.display_names(ps)
    keep = kept(rel, cards)
    given = hearsay_fill(allocate(keep, ps, 1, rel, ad), keep, rel)
    prompts = build_room(ps, names, adapter=ad, digest=d["digest"], target=d["target"], given=given, cards_by=cards,
                         leans=[p.get("lean") for p in ps], spec=spec, topic=topic)
    sharer = max(range(len(ps)), key=lambda i: (ad.static_score(ps[i], d["target"]), -i))

    if a.fake:
        lines = itertools.cycle(["밤 10시까지면 퇴근하고 들를 수 있겠네요", "(#1에 답장) 골목이 어두워서 걱정이에요", "(넘어감)",
                                 "시험 기간에 자리 잡기 좀 쉬워지려나요", "인건비는 어디서 나오는지 궁금하네요"])
        lane = FakeLane("base", lambda messages: next(lines), slots=2)
        lanes = {"base": lane}
        share = "다음 달부터 구립 도서관이 밤 10시까지 연다네요~^^ 퇴근하고 갈 수 있겠어요"
    else:
        base, key, model = os.environ["SARANGBANG_BASE_URL"], os.environ["SARANGBANG_API_KEY"], os.environ["SARANGBANG_MODEL"]
        lanes = {"base": Lane.openai("base", base, key, model, slots=2)}
        share = M.seed_message(JsonLLM.openai(base, key, model), d["title"], d["digest"], ad.seed_profile(ps[sharer], d["target"]), topic=topic)

    room = Room("r1", ps, names, prompts, d["target"], {"author": sharer, "text": share}, target_msgs=a.msgs,
                scorer=ad.static_score, topic=topic)

    def show(r: Room, m: dict) -> None:
        rep = f"(#{m['reply_to']}에 답장) " if m.get("reply_to") else ""
        print(f"#{m['id']:>3} {m['vt']['time']} {r.names[m['author']]}: {rep}{m['text']}")

    print(f"#  1 {room.msgs[0]['vt']['time']} {names[sharer]}: {share}")
    stats = asyncio.run(run_rooms([room], lanes, on_message=show))
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
