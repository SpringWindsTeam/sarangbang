"""시나리오 파일 — 주제·시민·카드를 JSON 하나에 담아 방 하나를 바로 돌린다. CLI `sarangbang run`과 예제가 쓴다.

내장 시나리오 "toy_library"(동네 도서관 야간 개관 · 시민 4명 · 카드 4장)가 형식의 본보기다(src/sarangbang/data/toy_library.json).

{
  "title": "동네 도서관 야간 개관",
  "topic": "generic",                      # 선택. "generic"(GENERIC_KO · ko_generic) | "policy"(POLICY_KO · ko_s12)
  "spec": "ko_generic",                    # 선택. 내장 사양 이름 또는 JSON 경로 — topic의 짝 사양을 덮어쓴다
  "digest": {"summary": "…", "facts": [{"statement": "…", "condition": "", "status": "확정·시행"}]},
  "target": {…},                           # 주제와 사람의 관계를 판단할 정보(어댑터·scorer에 그대로 전달)
  "cards": {"c1": {…}},                    # 쟁점 카드(cards.py 형식). 없어도 된다
  "relevance": {"c1": "direct"},           # 카드 관련성(material.relevance 결과). 없으면 모든 카드 direct
  "personas": [{"name": "마포", "me": "…", "lean": 0.4, "score": 3, …}],   # DictAdapter 레코드
  "share": "첫 메시지",                     # 선택. 없으면 LLM(material.seed_message)이 쓴다(--fake면 고정 문장)
  "per_person": 1,                         # 선택. 한 사람에게 줄 카드 장수(기본 1)
  "room_name": "…", "room_desc": "…",       # 선택. Scene 덮어쓰기
  "days": 1, "day_reset": false            # 선택. Room 인자
}
"""
from __future__ import annotations

import itertools
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from importlib import resources
from pathlib import Path
from typing import Any

from . import material as M
from .cards import allocate, hearsay_fill, kept
from .engine import Room
from .llm import FakeLane, JsonCall
from .persona import DictAdapter, PersonaAdapter
from .scene import KO, Scene
from .spec import PersonPrompt, build_room, load_spec
from .topic import GENERIC_KO, POLICY_KO, TopicAdapter

BUILTIN = ("toy_library",)
TOPICS = {"generic": (GENERIC_KO, "ko_generic"), "policy": (POLICY_KO, "ko_s12")}

# --fake 때 돌려 쓰는 문장(내장 시나리오용 — 흐름 확인이 목적이라 내용은 아무래도 좋다)
FAKE_LINES = ("밤 10시까지면 퇴근하고 들를 수 있겠네요", "(#1에 답장) 골목이 어두워서 걱정이에요", "(넘어감)",
              "시험 기간에 자리 잡기 좀 쉬워지려나요", "인건비는 어디서 나오는지 궁금하네요")
FAKE_SHARE = "다음 달부터 구립 도서관이 밤 10시까지 연다네요~^^ 퇴근하고 갈 수 있겠어요"


def load_scenario(name_or_path: str = "toy_library") -> dict:
    """내장 이름(toy_library) 또는 JSON 파일 경로."""
    p = Path(name_or_path)
    if p.suffix == ".json" or p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    if name_or_path in BUILTIN:
        return json.loads(resources.files("sarangbang.data").joinpath(f"{name_or_path}.json").read_text(encoding="utf-8"))
    raise FileNotFoundError(f"시나리오를 찾지 못했습니다: {name_or_path} (내장: {', '.join(BUILTIN)})")


def topic_and_spec(d: dict, *, topic: str | None = None, spec: str | None = None) -> tuple[TopicAdapter, dict]:
    """시나리오의 topic/spec 키(인자가 우선)로 주제 문구와 사양을 고른다."""
    t = topic or d.get("topic") or "generic"
    if t not in TOPICS:
        raise ValueError(f"topic은 {'|'.join(TOPICS)} 중 하나여야 합니다: {t}")
    tp, default_spec = TOPICS[t]
    return tp, load_spec(spec or d.get("spec") or default_spec)


@dataclass
class Prepared:
    personas: list[Any]
    names: list[str]
    prompts: list[PersonPrompt]
    given: list[list[dict]]
    leans: list[float | None]
    sharer: int                 # 첫 메시지를 올리는 사람(정적 점수 1위)
    topic: TopicAdapter
    spec: dict
    scene: Scene
    adapter: PersonaAdapter


def prepare(d: dict, *, adapter: PersonaAdapter | None = None, topic: str | None = None, spec: str | None = None,
            plugins: list | None = None) -> Prepared:
    """카드 배분 → 시민별 프롬프트. LLM 없이 끝난다(관련성은 시나리오에 적힌 값을 쓴다)."""
    ad = adapter or DictAdapter()
    tp, sp = topic_and_spec(d, topic=topic, spec=spec)
    ps = d["personas"]
    cards = d.get("cards") or {}
    rel = d.get("relevance") or {cid: "direct" for cid in cards}
    keep = kept(rel, cards)
    given = hearsay_fill(allocate(keep, ps, int(d.get("per_person", 1)), rel, ad), keep, rel) if keep else [[] for _ in ps]
    scene = KO
    if d.get("room_name") or d.get("room_desc"):
        scene = replace(KO, room_name=d.get("room_name") or KO.room_name, room_desc=d.get("room_desc") or KO.room_desc)
    names = ad.display_names(ps)
    leans = [p.get("lean") if isinstance(p, dict) else None for p in ps]
    target = d.get("target") or {}
    prompts = build_room(ps, names, adapter=ad, digest=d["digest"], target=target, given=given, cards_by=cards, leans=leans,
                         spec=sp, scene=scene, topic=tp, plugins=plugins)
    sharer = max(range(len(ps)), key=lambda i: (ad.static_score(ps[i], target), -i))
    return Prepared(ps, names, prompts, given, leans, sharer, tp, sp, scene, ad)


def seed_share(d: dict, prep: Prepared, llm: JsonCall | None) -> str:
    """첫 메시지 — 시나리오의 share → LLM(seed_message) → (둘 다 없으면) 고정 문장."""
    if d.get("share"):
        return str(d["share"])
    if llm is not None:
        return M.seed_message(llm, d["title"], d["digest"], prep.adapter.seed_profile(prep.personas[prep.sharer], d.get("target") or {}),
                              topic=prep.topic)
    return FAKE_SHARE


def make_room(d: dict, prep: Prepared, share: str, *, target_msgs: int = 30, room_id: str = "r1", plugins: list | None = None,
              **room_kw) -> Room:
    kw = {"days": int(d.get("days", 1)), "day_reset": bool(d.get("day_reset", False)), **room_kw}
    return Room(room_id, prep.personas, prep.names, prep.prompts, d.get("target") or {}, {"author": prep.sharer, "text": share},
                target_msgs=target_msgs, scorer=prep.adapter.static_score, scene=prep.scene, room_name=prep.scene.room_name,
                topic=prep.topic, plugins=plugins or [], **kw)


def fake_lane(name: str = "base", lines: tuple[str, ...] = FAKE_LINES, slots: int = 2) -> FakeLane:
    """정해 둔 문장을 돌려 가며 답하는 레인(네트워크 없음)."""
    it = itertools.cycle(lines)
    return FakeLane(name, lambda messages: next(it), slots=slots)


def format_line(room: Room, m: dict) -> str:
    """단톡방 한 줄: '#  3 10:12 은평: (#1에 답장) …'."""
    who = room.scene.notice if m.get("kind") == "inject" else room.names[m["author"]]
    rep = f"(#{m['reply_to']}에 답장) " if m.get("reply_to") else ""
    return f"#{m['id']:>3} {m['vt']['time']} {who}: {rep}{m['text']}"


def transcript(d: dict, room: Room, stats: dict | None = None) -> dict:
    """저장용 결과 — 시나리오 제목·방 설정·메시지·호출 기록."""
    return {"title": d.get("title"), "room_id": room.room_id, "names": room.names, "target_msgs": room.target_msgs,
            "stop": room.stop_reason(), "stats": stats or {}, "messages": room.msgs, "calls": room.calls}


OnLine = Callable[[str], None]
