"""수집한 글·댓글(JSONL) → 쟁점 카드(cards.json). 기준은 docs/03-cards.md.

    python -m kb_tools.make_cards 수집글.jsonl -o knowledge-bases/my-topic/cards.json --title "공영주차장 야간 유료화"

입력 한 줄: {"text": "...", "platform": "cafe|blog|...", "kind": "시민 의견|단체 성명|기사 옮김", "date": "..."}
이 프롬프트는 비교 시험을 거치지 않은 출발점이다. 결과는 반드시 사람이 검수한다.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .kb import LEANS, llm_from_env

BATCH = 30          # 한 번에 넘기는 글 수
TEXT_CHARS = 500    # 글마다 자르는 길이
HEDGES = ("가능성", "수 있", "불명확", "우려", "것 같", "듯", "여부")   # 추측·바람은 전제가 아니다

SYSTEM = f"""너는 사람들이 쓴 글에서, 이 소식을 두고 단톡방에서 꺼낼 만한 관심사를 카드로 정리한다.
규칙
- 카드 하나에 관심사 하나. 한 글에 관심사가 둘이면 카드 두 장.
- name은 2~8자 명사구, interest는 무엇이 궁금하거나 걱정되는지 20자 안팎의 구절. 글의 표현을 그대로 옮기지 않는다.
- ask_form은 이 관심사를 가진 사람이 던질 법한 짧은 질문 하나(25자 이내, 반말·존댓말 상관없음). 글의 표현·개인 사정(가족, 시간 등)을 옮기지 않는다.
- perspective는 이 관심사가 나오는 관점(예: 이용자, 구매 예정자, 기존 고객, 시청자, 팬, 인근 주민, 직원). 모르면 빈 문자열.
- arg_types는 논거 유형 1~2개(예: 비용, 품질, 편의, 안전, 공정, 신뢰, 취향, 시간).
- lean은 {' / '.join(LEANS)} 중 하나.
- outside_fact는 글에 나온 '다른 곳 사례'나 '직접 본 현상' 하나(예: "옆 동네는 유료화 뒤 골목 주차가 늘었다"). 없으면 빈 문자열.
  scope(범위)·time(시기)은 글에 나온 대로, 없으면 '범위 미상'·'시기 미상'.
- 기사 내용을 옮기기만 한 글, 소식 자체를 전달하기만 한 글은 카드로 만들지 않는다.
- src는 그 관심사가 나온 글 번호 목록.
JSON으로만 답한다: {{"cards": [{{"name": "...", "interest": "...", "ask_form": "...", "perspective": "...", "arg_types": ["..."],
"lean": "...", "outside_fact": "", "scope": "", "time": "", "src": [0]}}]}}"""


def _premises(c: dict) -> list[dict]:
    fact = str(c.get("outside_fact") or "").strip()
    if not fact or any(h in fact for h in HEDGES):
        return []
    return [{"premise": fact, "scope": c.get("scope") or "범위 미상", "time": c.get("time") or "시기 미상"}]


def make_cards(llm, title: str, posts: list[dict]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for o in range(0, len(posts), BATCH):
        part = posts[o:o + BATCH]
        body = "\n".join(f"{k}. ({p.get('platform', '')}) {str(p.get('text', ''))[:TEXT_CHARS]}" for k, p in enumerate(part))
        d, _ = llm(SYSTEM, f"[소식] {title}\n[글 {len(part)}개]\n{body}", max_tokens=4000)
        for c in d.get("cards") or []:
            if not c.get("name") or c.get("lean") not in LEANS:
                continue
            src = [part[i] for i in c.get("src") or [] if isinstance(i, int) and 0 <= i < len(part)]
            key = c["name"].strip()
            if key in merged:                      # 이름이 같으면 합친다(빈도 합산, 전제 추가)
                merged[key]["freq"] += max(1, len(src))
                merged[key]["premises"] += _premises(c)
                continue
            merged[key] = {"name": key, "interest": c.get("interest", ""), "ask_form": c.get("ask_form", ""),
                           "perspective": c.get("perspective", ""), "arg_types": c.get("arg_types") or ["기타"],
                           "freq": max(1, len(src)), "stance_lean": {"lean": c["lean"]}, "premises": _premises(c),
                           "sources": [{"kind": s.get("kind", "시민 의견"), "platform": s.get("platform", "")} for s in src[:1]]
                           or [{"kind": "시민 의견", "platform": ""}]}
    out: dict[str, dict] = {}
    for k, c in enumerate(sorted(merged.values(), key=lambda c: -c["freq"]), start=1):
        cid = f"c{k}"
        out[cid] = {"id": cid, **c}
        if not out[cid]["perspective"]:
            del out[cid]["perspective"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="수집 글에서 쟁점 카드 만들기")
    ap.add_argument("source", help="JSONL, 한 줄에 글 하나")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--title", required=True)
    a = ap.parse_args()
    posts = [json.loads(line) for line in Path(a.source).read_text(encoding="utf-8").splitlines() if line.strip()]
    cards = make_cards(llm_from_env(), a.title, posts)
    Path(a.out).write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"글 {len(posts)}개 → 카드 {len(cards)}장 → {a.out}. 원글 문장 복사·찬반 균형·관점을 검수하세요.")


if __name__ == "__main__":
    main()
