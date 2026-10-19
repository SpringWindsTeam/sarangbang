"""쟁점 카드 배분 — 방 안 시민에게 카드를 나눈다(무작위 없음).

카드: {id, name, interest, ask_form?, perspective?, require?, arg_types?: [..], freq: int, stance_lean: {lean: 찬성|반대|조건부|중립},
       premises?: [{premise, scope?, time?, source_kind?}], sources?: [{kind, platform?, title?}]}
rel_of: 카드 id → direct|related|unrelated (material.relevance 결과)

배분: 논거 유형 순환 + 기울기 번갈아, 관점·필수 처지 지킴(adapter.card_fits), 자기 관점 카드 먼저, 첫 장은 direct 우선,
한 사람 per_person장, 카드당 1명.
"""
from __future__ import annotations

import collections
from typing import Any

from .persona import PersonaAdapter


def kept(rel_of: dict[str, str], cards: dict[str, dict]) -> list[dict]:
    """관련성 판정에서 direct·related인 카드(id 순)."""
    return [cards[cid] for cid in sorted(rel_of) if cid in cards and rel_of[cid] in ("direct", "related")]


def allocate(cards: list[dict], personas: list[Any], per_person: int, rel_of: dict[str, str],
             adapter: PersonaAdapter) -> list[list[dict]]:
    """→ 사람마다 [{card, name, interest, ask_form, perspective, rel, arg_type, direction}]."""
    by_type: dict[str, list] = collections.defaultdict(list)
    for c in cards:
        by_type[(c.get("arg_types") or ["기타"])[0]].append(c)
    queues = {}
    for t, cs in by_type.items():
        by_dir: dict[str, list] = collections.defaultdict(list)
        for c in sorted(cs, key=lambda c: (rel_of[c["id"]] != "direct", -c["freq"], c["id"])):
            by_dir[c["stance_lean"]["lean"]].append(c)
        order = []
        while any(by_dir.values()):
            for d in ("찬성", "반대", "조건부", "중립"):
                if by_dir[d]:
                    order.append(by_dir[d].pop(0))
        queues[t] = order
    types = sorted(queues, key=lambda t: -len(queues[t]))
    pool: list[dict] = []
    while any(queues.values()):
        for t in types:
            if queues[t]:
                pool.append(queues[t].pop(0))
    persp = [adapter.own_perspectives(p) for p in personas]
    per: list[list[dict]] = [[] for _ in personas]
    for rnd in range(per_person):
        for i in range(len(personas)):
            order = sorted(range(len(pool)), key=lambda k: (rnd == 0 and rel_of[pool[k]["id"]] != "direct",
                                                            pool[k].get("perspective") not in persp[i], k))
            for k in order:
                c = pool[k]
                if adapter.card_fits(c, personas[i]):
                    per[i].append({"card": c["id"], "name": c["name"], "interest": c["interest"], "ask_form": c.get("ask_form", ""),
                                   "perspective": c.get("perspective", ""), "rel": rel_of[c["id"]],
                                   "arg_type": (c.get("arg_types") or ["기타"])[0], "direction": c["stance_lean"]["lean"]})
                    pool.pop(k)
                    break
    return per


def hearsay_fill(given: list[list[dict]], keep: list[dict], rel_of: dict[str, str]) -> list[list[dict]]:
    """카드를 못 받은 사람에게 아직 안 쓴 관련 카드 한 장을 '들은 얘기'로만(관심사 칸 없이) — direct 먼저 → 빈도 높은 순 → id.
    관점·처지 조건은 보지 않는다(남의 처지 얘기를 들은 것이므로)."""
    used = {x["card"] for v in given for x in v}
    pool = sorted((c for c in keep if c["id"] not in used), key=lambda c: (rel_of.get(c["id"]) != "direct", -c["freq"], c["id"]))
    out = [list(v) for v in given]
    for i, v in enumerate(out):
        if not v and pool:
            out[i] = [{"card": pool.pop(0)["id"], "hearsay_only": True}]
    return out
