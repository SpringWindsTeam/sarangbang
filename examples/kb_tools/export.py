"""지식 베이스 폴더 → sarangbang 시나리오 JSON 한 파일. `sarangbang run`으로 바로 돌릴 수 있다.

    python -m kb_tools.export knowledge-bases/local-news -o local-news.json
    sarangbang run local-news.json --fake --msgs 12

시나리오 형식이 담지 못하는 것(내보내면 빠짐):
- topic의 noun · label · relation_label · common_words — 시나리오는 "generic" | "policy"만 고른다. 바꾼 문구가 필요하면 kb_tools.run을 쓴다.
- 연결 의견(links) — sarangbang run은 연결 의견을 만들지 않는다.
- hearsay: false — sarangbang run은 들은 얘기를 항상 채운다.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .kb import load_kb

TOPIC_EXTRAS = ("noun", "label", "relation_label", "common_words")


def to_scenario(root: str | Path) -> tuple[dict, list[str]]:
    """(시나리오 dict, 빠진 것 안내 목록)."""
    kb = load_kb(root)
    m = kb.meta
    topic_cfg = m.get("topic") or {}
    d = {"title": kb.title, "topic": topic_cfg.get("base", "generic"), "digest": kb.digest, "target": kb.target,
         "cards": kb.cards, "personas": kb.personas, "per_person": m.get("cards_per_person", 1)}
    if m.get("spec"):
        d["spec"] = m["spec"]
    if kb.relevance is not None:
        d["relevance"] = kb.relevance
    for k in ("room_name", "room_desc", "days", "day_reset", "share"):
        if k in m:
            d[k] = m[k]
    notes = []
    lost = [k for k in TOPIC_EXTRAS if topic_cfg.get(k)]
    if lost:
        notes.append(f"topic의 {', '.join(lost)}는 시나리오 형식에 없어 빠집니다(기본 문구 사용)")
    if kb.relevance is None:
        notes.append("relevance.json이 없어 sarangbang run은 모든 카드를 direct로 봅니다")
    if m.get("hearsay") is False:
        notes.append("hearsay: false는 시나리오 형식에 없어 빠집니다")
    return d, notes


def main() -> None:
    ap = argparse.ArgumentParser(description="지식 베이스 폴더를 sarangbang 시나리오 JSON으로")
    ap.add_argument("root")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    d, notes = to_scenario(a.root)
    Path(a.out).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"→ {a.out}  (sarangbang run {a.out} --fake)")
    for n in notes:
        print(f"  [안내] {n}")


if __name__ == "__main__":
    main()
