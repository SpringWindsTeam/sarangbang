"""지식 베이스 폴더 하나로 단톡방 실행 — 관련성 판정 → 연결 의견 → 카드 배분 → 방 실행 → out/<이름>/ 저장.

    python -m kb_tools.run knowledge-bases/local-news --fake --msgs 12      # 모델 없이 흐름 확인
    python -m kb_tools.run knowledge-bases/local-news --msgs 40             # 실제 모델

실제 모델은 sarangbang의 환경 변수 규칙을 따른다(기본 레인·재료 준비):
  SARANGBANG_PROVIDER=friendli|vllm|upstage|… (+ SARANGBANG_MODEL)  또는  SARANGBANG_BASE_URL · SARANGBANG_API_KEY · SARANGBANG_MODEL
앵커 레인(선택): 같은 규칙에 접두사 SARANGBANG_ANCHOR_ — 점수 상위 1/6 시민이 이 모델로 말한다(예: 앵커 A.X, 기본 EXAONE).
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import itertools
import json
from pathlib import Path

from sarangbang import DictAdapter, FakeLane, Room, allocate, build_room, hearsay_fill, kept, lane_from_env, run_rooms
from sarangbang import material as M
from sarangbang.providers import configured

from .kb import KB, llm_from_env, load_kb


def prepare(kb: KB, *, fake: bool) -> tuple[dict[str, str], dict[str, str]]:
    """(카드 id → 관련성, 카드 id → 연결 의견). relevance.json이 있으면 그대로 쓴다."""
    if kb.relevance is not None:
        rel = dict(kb.relevance)
    elif fake:
        rel = {cid: "related" for cid in kb.cards}
    else:
        rel, _ = M.relevance(llm_from_env(), M.head(kb.title, kb.digest, kb.topic), list(kb.cards.values()), topic=kb.topic)
    links: dict[str, str] = {}
    if not fake:
        links, _ = M.links(llm_from_env(), M.head(kb.title, kb.digest, kb.topic), kept(rel, kb.cards), topic=kb.topic)
    return rel, links


def fake_lines(kb: KB):
    """모델 없이 돌릴 때 쓸 답 — 카드의 질문 꼴과 넘어감을 번갈아."""
    asks = [c["ask_form"] for c in kb.cards.values() if c.get("ask_form")] or ["그렇군요"]
    seq = []
    for k, a in enumerate(asks):
        seq.append(f"(#{k + 1}에 답장) {a}" if k % 3 == 1 else a)
        if k % 2:
            seq.append("(넘어감)")
    return itertools.cycle(seq)


def lanes_for(fake: bool, kb: KB) -> dict:
    if fake:
        it = fake_lines(kb)
        return {"base": FakeLane("base", lambda messages: next(it), slots=2)}
    try:
        lanes = {"base": lane_from_env("base", slots=4)}
        if configured("SARANGBANG_ANCHOR"):
            lanes["anchor"] = lane_from_env("anchor", prefix="SARANGBANG_ANCHOR")
    except KeyError as e:
        raise SystemExit(str(e).strip("'\"")) from None
    return lanes


def run(root: str | Path, *, fake: bool = False, msgs: int = 40, days: int = 1, out_dir: str | Path = "out", quiet: bool = False) -> dict:
    kb = load_kb(root)
    ad = DictAdapter()
    ps = kb.personas
    names = ad.display_names(ps)
    rel, links = prepare(kb, fake=fake)
    keep = kept(rel, kb.cards)
    given = allocate(keep, ps, kb.meta.get("cards_per_person", 1), rel, ad)
    if kb.meta.get("hearsay", True):
        given = hearsay_fill(given, keep, rel)
    given = [[{**x, "link": links.get(x["card"], "")} for x in v] for v in given]
    prompts = build_room(ps, names, adapter=ad, digest=kb.digest, target=kb.target, given=given, cards_by=kb.cards,
                         leans=[p.get("lean") for p in ps], spec=kb.spec, topic=kb.topic)
    sharer = max(range(len(ps)), key=lambda i: (ad.static_score(ps[i], kb.target), -i))
    if fake:
        share = kb.meta.get("fake_share") or f"{kb.title} 소식 보셨어요?"
    else:
        share = M.seed_message(llm_from_env(), kb.title, kb.digest, ad.seed_profile(ps[sharer], kb.target), topic=kb.topic)

    room = Room(kb.name, ps, names, prompts, kb.target, {"author": sharer, "text": share}, target_msgs=msgs, days=days,
                scorer=ad.static_score, topic=kb.topic, room_name=kb.meta.get("room_name"))
    out = Path(out_dir) / kb.name
    out.mkdir(parents=True, exist_ok=True)
    log = (out / "messages.jsonl").open("w", encoding="utf-8")

    def write(m: dict) -> None:
        log.write(json.dumps({"id": m["id"], "time": m["vt"], "name": names[m["author"]] if m["author"] >= 0 else "알림",
                              "reply_to": m.get("reply_to"), "text": m["text"], "model": m.get("model")}, ensure_ascii=False) + "\n")
        if not quiet:
            rep = f"(#{m['reply_to']}에 답장) " if m.get("reply_to") else ""
            who = names[m["author"]] if m["author"] >= 0 else "알림"
            print(f"#{m['id']:>3} {m['vt']['day']}일차 {m['vt']['time']} {who}: {rep}{m['text']}")

    write(room.msgs[0])
    stats = asyncio.run(run_rooms([room], lanes_for(fake, kb), on_message=lambda r, m: write(m)))
    log.close()
    (out / "prompts.json").write_text(json.dumps(
        [{"name": names[i], "given": given[i], **dataclasses.asdict(p)} for i, p in enumerate(prompts)],
        ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"kb": kb.name, "messages": len(room.msgs), "stop": stats["rooms"][0]["stop"], "calls": stats["calls"],
               "sec": stats["sec"], "with_cards": sum(1 for v in given if any(not x.get("hearsay_only") for x in v)),
               "personas": len(ps)}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="지식 베이스로 단톡방 실행")
    ap.add_argument("root")
    ap.add_argument("--fake", action="store_true", help="모델 없이 정해 둔 답으로")
    ap.add_argument("--msgs", type=int, default=40, help="목표 메시지 수")
    ap.add_argument("--days", type=int, default=1, help="가상 일수")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    s = run(a.root, fake=a.fake, msgs=a.msgs, days=a.days, out_dir=a.out)
    print(json.dumps(s, ensure_ascii=False))
    print(f"결과: {Path(a.out) / s['kb']}/ (messages.jsonl · prompts.json · summary.json)")


if __name__ == "__main__":
    main()
