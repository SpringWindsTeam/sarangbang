"""재료 준비(LLM) — 주제 하나에 대해 시민과 무관하게 미리 만들 수 있는 것.

- relevance: 쟁점 카드 후보마다 이 주제 대화에 나올 만한가(direct|related|unrelated) — 60장씩, 동시 workers
- links: 카드마다 '이 주제와 이 쟁점을 어떻게 잇는지' 1인칭 한 줄 — 40장씩, 동시 workers
- seed_message: 방에 처음 올릴 공유 메시지(첫 발화자에 대한 사실을 받아 한두 문장)

프롬프트 문구는 주제 어댑터(topic.Topic)가 정한다. 주제 사실층(digest)·후보 카드 고르기(분류 체계)는 도메인마다 달라
쓰는 쪽이 만든다. llm은 (system, user, max_tokens=) → (JSON, 초) 호출 가능 객체다(예: llm.JsonLLM).
"""
from __future__ import annotations

import concurrent.futures as cf

from .llm import JsonCall
from .topic import GENERIC_KO, TopicAdapter

REL_CHUNK = 60
LINK_CHUNK = 40


def head(title: str, digest: dict, topic: TopicAdapter = GENERIC_KO) -> str:
    """카드 판정·연결 의견 호출에 붙이는 주제 머리(이름 + 요약 + 사실 목록)."""
    return topic.head(title, digest)


def relevance(llm: JsonCall, head: str, cand: list[dict], workers: int = 3, *,
              topic: TopicAdapter = GENERIC_KO) -> tuple[dict[str, str], list[float]]:
    """카드 id → direct|related|unrelated (판정 없으면 빠짐), 호출별 초."""
    parts = [(o, cand[o:o + REL_CHUNK]) for o in range(0, len(cand), REL_CHUNK)]

    def one(args):
        off, part = args
        b = "\n".join(f"{off + k}. {c['name']} — {c.get('claim') or ''} (원글: {(c.get('sources') or [{}])[0].get('title', '')[:40]})"
                      for k, c in enumerate(part))
        d, sec = llm(topic.relevance_system, f"{head}\n\n[쟁점 카드 {len(part)}개]\n{b}", max_tokens=4000)
        return sec, {cand[int(x["i"])]["id"]: x["rel"] for x in d.get("labels") or []
                     if str(x.get("i", "")).isdigit() and int(x["i"]) < len(cand)}
    rel_of: dict[str, str] = {}
    secs: list[float] = []
    if not parts:
        return rel_of, secs
    with cf.ThreadPoolExecutor(workers) as ex:
        for sec, d in ex.map(one, parts):
            rel_of.update(d)
            secs.append(sec)
    return rel_of, secs


def links(llm: JsonCall, head: str, used: list[dict], workers: int = 3, *,
          topic: TopicAdapter = GENERIC_KO) -> tuple[dict[str, str], list[float]]:
    """카드 id → 연결 의견 한 줄, 호출별 초."""
    parts = [used[o:o + LINK_CHUNK] for o in range(0, len(used), LINK_CHUNK)]

    def one(part):
        b = "\n".join(f"{k}. {c['interest']} — {c.get('claim') or ''}" for k, c in enumerate(part))
        d, sec = llm(topic.link_system, f"{head}\n\n[카드 {len(part)}개]\n{b}", max_tokens=3000)
        return sec, {part[int(x["i"])]["id"]: x["link"] for x in d.get("links") or []
                     if str(x.get("i", "")).isdigit() and int(x["i"]) < len(part)}
    out: dict[str, str] = {}
    secs: list[float] = []
    if not parts:
        return out, secs
    with cf.ThreadPoolExecutor(min(workers, len(parts))) as ex:
        for sec, d in ex.map(one, parts):
            out.update(d)
            secs.append(sec)
    return out, secs


def seed_message(llm: JsonCall, title: str, digest: dict, who: list[str], *, topic: TopicAdapter = GENERIC_KO) -> str:
    """첫 공유 메시지. who는 첫 발화자에 대한 사실 줄(adapter.seed_profile)."""
    lines = "\n".join(f"- {x}" for x in who if x)
    body = topic.head(title, {**digest, "facts": [{"statement": f.get("statement")} for f in digest.get("facts") or []]})
    d, _ = llm(topic.seed_system, f"{body}\n\n[그 사람에 대한 사실]\n{lines}", max_tokens=300)
    text = str(d.get("text") or "").strip().strip('"“”')
    if not text:
        raise RuntimeError("첫 메시지를 만들지 못했습니다")
    return text
