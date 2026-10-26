"""지식 베이스 점검 — 형식 오류(error)와 구성 경고(warn).

    python -m kb_tools.validate knowledge-bases/local-news
    python -m kb_tools.validate knowledge-bases/*        # 여러 폴더
"""
from __future__ import annotations

import argparse
import collections
import sys

from .kb import LEANS, RELS, load_kb


def check(root) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    try:
        kb = load_kb(root)
    except FileNotFoundError as e:
        return [f"파일 없음: {e.filename}"], []

    # meta
    if not kb.meta.get("title"):
        errors.append("meta.json: title이 비었습니다")

    # digest
    facts = kb.digest.get("facts") or []
    if not kb.digest.get("summary"):
        errors.append("digest.json: summary가 비었습니다")
    if not facts:
        errors.append("digest.json: facts가 비었습니다")
    for i, f in enumerate(facts):
        if not f.get("statement"):
            errors.append(f"digest.json facts[{i}]: statement가 비었습니다")
        if f.get("status") not in kb.statuses:
            warns.append(f"digest.json facts[{i}]: status {f.get('status')!r} — "
                         f"meta.json statuses(없으면 기본값)는 {' / '.join(kb.statuses)} (엔진은 적힌 대로 보여 줌)")
    if facts and not 5 <= len(facts) <= 15:
        warns.append(f"digest.json: 사실이 {len(facts)}개입니다. 8~12개를 권장합니다")
    if kb.digest.get("not_stated"):
        warns.append("digest.json: not_stated(원문에 없는 것)가 있습니다. '그런 얘기는 없던데' 같은 말이 되풀이될 수 있어 비우기를 권장합니다")

    # cards
    for cid, c in kb.cards.items():
        where = f"cards.json {cid}"
        if c.get("id") != cid:
            errors.append(f"{where}: id가 키와 다릅니다")
        for k in ("name", "interest", "arg_types"):
            if not c.get(k):
                errors.append(f"{where}: {k}가 비었습니다")
        if not isinstance(c.get("freq"), int) or c["freq"] < 1:
            errors.append(f"{where}: freq는 1 이상의 정수여야 합니다")
        if (c.get("stance_lean") or {}).get("lean") not in LEANS:
            errors.append(f"{where}: stance_lean.lean은 {' / '.join(LEANS)} 중 하나여야 합니다")
        for p in c.get("premises") or []:
            if not p.get("scope") or not p.get("time"):
                warns.append(f"{where}: premises에 scope·time이 비었습니다(모르면 '범위 미상'·'시기 미상')")
        if len(c.get("interest", "")) > 40:
            warns.append(f"{where}: interest가 깁니다. 원글 문장 대신 짧은 구절로 줄이세요")

    leans = collections.Counter((c.get("stance_lean") or {}).get("lean") for c in kb.cards.values())
    if kb.cards and set(leans) != {"중립"}:          # 전부 중립이면 찬반 축이 없는 주제로 보고 균형 점검을 건너뜀
        top, n = leans.most_common(1)[0]
        if n / len(kb.cards) >= 0.7:
            warns.append(f"cards.json: 카드의 {n}/{len(kb.cards)}장이 '{top}'입니다. 찬반 방향을 고르게 하세요")
        missing = [d for d in LEANS if d not in leans]
        if missing:
            warns.append(f"cards.json: {', '.join(missing)} 방향 카드가 없습니다")

    # relevance
    if kb.relevance is not None:
        for cid, r in kb.relevance.items():
            if cid not in kb.cards:
                errors.append(f"relevance.json: 없는 카드 {cid}")
            if r not in RELS:
                errors.append(f"relevance.json {cid}: {' / '.join(RELS)} 중 하나여야 합니다")
        unjudged = [cid for cid in kb.cards if cid not in kb.relevance]
        if unjudged:
            warns.append(f"relevance.json: 판정이 없는 카드 {', '.join(unjudged)} (배분에서 빠집니다)")

    # personas
    if not kb.personas:
        errors.append("personas.json: 시민이 없습니다")
    names = [p.get("name") for p in kb.personas]
    dup = [n for n, k in collections.Counter(names).items() if n and k > 1]
    if dup:
        errors.append(f"personas.json: 표시 이름이 겹칩니다 ({', '.join(dup)})")
    for i, p in enumerate(kb.personas):
        if not p.get("me"):
            warns.append(f"personas.json [{i}] {p.get('name')}: me가 비었습니다")
        lv = p.get("lean")
        if lv is not None and not -1 <= lv <= 1:
            errors.append(f"personas.json [{i}] {p.get('name')}: lean은 -1~1 또는 null이어야 합니다")
    tags = {t for p in kb.personas for t in p.get("situation") or []}
    for cid, c in kb.cards.items():
        need = c.get("require") or []
        unknown = [t for t in need if t not in tags]
        if unknown:
            warns.append(f"cards.json {cid}: require 태그 {', '.join(unknown)}를 가진 시민이 없습니다(이 카드는 배분되지 않음)")

    per = kb.meta.get("cards_per_person", 1)
    usable = [c for cid, c in kb.cards.items() if kb.relevance is None or kb.relevance.get(cid) in ("direct", "related")]
    if len(usable) < len(kb.personas) * per:
        warns.append(f"카드 {len(usable)}장 < 시민 {len(kb.personas)}명 × {per}장. 뒤쪽 시민은 카드를 받지 못합니다")
    return errors, warns


def main() -> None:
    ap = argparse.ArgumentParser(description="지식 베이스 점검")
    ap.add_argument("roots", nargs="+")
    a = ap.parse_args()
    bad = False
    for root in a.roots:
        errors, warns = check(root)
        print(f"== {root}: 오류 {len(errors)} · 경고 {len(warns)}")
        for e in errors:
            print(f"  [오류] {e}")
        for w in warns:
            print(f"  [경고] {w}")
        bad = bad or bool(errors)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
