"""대화 기록 렌더 — 단톡방 화면 그대로의 텍스트(JSON 피드·영어 래퍼 없음)와 '이미 많이 나온 말'(모델 판정 없이)."""
from __future__ import annotations

import collections
import re

from .scene import KO, Scene


def render_log(msgs: list[dict], names: list[str], me: int, n_members: int, closing: str, before_closing: str = "",
               *, scene: Scene = KO, room_name: str | None = None, window: int | None = None,
               common_words: frozenset[str] = frozenset(), context: str = "") -> str:
    """최근 window개 + 공유 메시지(#1) + 내 말·나에게 온 답장은 창 밖이어도 남긴다.

    msgs: [{id, author(방 안 번호), text, reply_to?, kind?, reactions?}]. closing은 마무리 지시, before_closing은 그 바로 앞 꼬리.
    context는 이 호출에만 넣는 문맥(PromptPlugin.call_context) — 대화 기록과 꼬리 사이. common_words는 주제 일반어."""
    window = scene.window if window is None else window
    keep_ids = {m["id"] for m in msgs[-window:]}
    keep_ids.add(1)
    mine = {m["id"] for m in msgs if m["author"] == me}
    keep_ids |= mine
    keep_ids |= {m["id"] for m in msgs if m.get("reply_to") in mine}
    lines = [f"[{room_name or scene.room_name} · {n_members}명]"]
    prev = 0
    for m in msgs:
        if m["id"] not in keep_ids:
            continue
        if prev and m["id"] - prev > 1:
            lines.append(scene.gap)
        prev = m["id"]
        who = scene.notice if m.get("kind") == "inject" else (scene.me if m["author"] == me else names[m["author"]])
        body = m["text"]
        if m.get("reply_to"):
            body = f"(#{m['reply_to']}에 답장) " + body
        rs = len(m.get("reactions") or [])
        lines.append(f"#{m['id']} {who}: " + body + (f"  [공감 {rs}]" if rs else ""))
    sat = saturated_terms(msgs, scene=scene, common_words=common_words)
    tail = (f"(이미 여러 사람이 많이 한 말: {', '.join(sat)})\n\n" if sat else "") + closing
    mid = (f"\n\n{context}" if context else "") + (f"\n\n{before_closing}" if before_closing else "")
    return "\n".join(lines) + mid + "\n\n" + tail


def _toks(t: str, josa: tuple[str, ...]) -> list[str]:
    out = []
    for w in re.findall(r"[가-힣]{2,}", t):
        for j in josa:
            if w.endswith(j) and len(w) - len(j) >= 1:
                w = w[: -len(j)]
                break
        out.append(w)
    return out


def saturated_terms(msgs: list[dict], k: int = 3, min_people: int = 4, recent: int = 30, *, scene: Scene = KO,
                    common_words: frozenset[str] = frozenset()) -> list[str]:
    """최근 대화에서 서로 다른 min_people명 이상이 쓴 '두 낱말 묶음'(조사 뗀 낱말 기준) 상위 k개.
    두 낱말이 모두 일반어면 뺀다. 묶음끼리 낱말이 겹치면 사람이 더 많은 쪽만."""
    stop = scene.sat_stop | common_words
    who: dict[str, set] = collections.defaultdict(set)
    for m in msgs[-recent:]:
        if m["id"] == 1:
            continue
        ws = _toks(m["text"], scene.josa)
        for x, y in zip(ws, ws[1:]):
            if (x in stop or len(x) < 2) and (y in stop or len(y) < 2):
                continue
            if x.endswith(("다", "고", "면", "서", "며", "는", "던", "을", "인")) or x.endswith("것만으로") or y.endswith("것만으로"):
                continue  # '있다 것만으로', '한다 말씀'처럼 서술어가 앞에 오는 묶음 제외
            who[f"{x} {y}"].add(m["author"])
    top = sorted(((len(v), g) for g, v in who.items() if len(v) >= min_people), reverse=True)
    out: list[str] = []
    used: set[str] = set()
    for _, g in top:
        if set(g.split()) & used:
            continue
        out.append(g)
        used |= set(g.split())
        if len(out) == k:
            break
    return out
