"""프롬프트 사양 렌더 — 방 하나의 시민별 system·마무리 앞 꼬리를 재료에서 조립한다.

사양 JSON(specs/*.json)은 칸 이름·문구·켜고 끄는 항목을 담는다. 내장 사양:
- ko_s12: 한국어 교육정책 시뮬레이션에서 비교 시험으로 고른 문구(주제 POLICY_KO와 짝)
- ko_generic: ko_s12에서 정책 낱말만 범용으로 바꾼 것(주제 GENERIC_KO와 짝, 기본값)
문구를 바꾸면 같은 판정으로 다시 시험할 것.

재료
- digest: 주제 사실층 {summary, facts: [{statement, condition?, status?}], not_stated?: [{question}]}
- target: 주제와 사람의 관계를 판단할 정보(어댑터가 해석한다 — 엔진은 들여다보지 않는다)
- given[i]: i번 시민에게 배분된 카드 [{card: id, link?, hearsay_only?}]
- cards_by: 카드 id → 카드 {interest, ask_form?, premises?, sources?, stance_lean: {lean}, perspective?, require?}
- leans[i]: 입장 기울기(-1~1 또는 None)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import plugins as PL
from .persona import PersonaAdapter
from .scene import KO, Scene
from .topic import GENERIC_KO, TopicAdapter

SPEC_DIR = Path(__file__).resolve().parent / "specs"
DEFAULT_SPEC = "ko_generic"   # 범용. 교육정책 시험 문구는 "ko_s12"(POLICY_KO 주제와 함께)


@lru_cache(maxsize=8)
def _load(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_spec(name_or_path: str = DEFAULT_SPEC) -> dict:
    """내장 사양 이름(specs/<이름>.json) 또는 JSON 파일 경로."""
    p = Path(name_or_path)
    path = p if p.suffix == ".json" and p.exists() else SPEC_DIR / f"{name_or_path}.json"
    d = json.loads(_load(str(path)))
    d["_id"] = p.stem if p.suffix == ".json" else name_or_path
    return d


@dataclass
class PersonPrompt:
    system: str
    before_closing: str  # 마무리 지시 바로 앞(입장 머리 문장·가벼운 찬성·신상 요약)
    closing: str
    stance_tier: str = "없음"
    light_support: bool = False
    hearsay: str = ""
    cards: list[dict] = field(default_factory=list)


def system_message(name: str, sections: list[str], rule: str = "", *, scene: Scene = KO, room_name: str | None = None) -> str:
    """장면 한 줄 + 사실 섹션 + 공통 규칙 + 사양 규칙."""
    sc = scene if not room_name or room_name == scene.room_name else replace(scene, room_name=room_name)
    return sc.intro(name) + "\n".join(sections) + "\n\n" + sc.rules + (("\n" + rule) if rule else "")


def src_phrase(card: dict) -> str:
    """[들은 얘기]의 출처 표현 — 카드 sources[0]의 kind·platform."""
    s0 = (card.get("sources") or [{}])[0]
    kind = s0.get("kind", "")
    if kind == "단체 성명":
        return "어느 단체 성명"
    if kind == "기사 옮김":
        return "옮겨진 기사"
    return "블로그 글" if (s0.get("platform") == "blog" or "blog.naver" in s0.get("link", "")) else "온라인 카페 글"


def premise_of(card: dict) -> dict | None:
    """카드 전제 중 하나 — 구체적인 것 먼저(범위·시기가 밝혀지고 숫자가 있는 것), 같은 점수면 카드에 적힌 순서."""
    ps_ = [x for x in card.get("premises") or [] if x.get("source_kind") != "기사 옮김"] or (card.get("premises") or [])
    return max(ps_, key=lambda x: (("미상" not in (x.get("scope") or "미상")) * 2 + ("미상" not in (x.get("time") or "미상"))
                                  + bool(re.search(r"\d", x.get("premise") or "")), -ps_.index(x))) if ps_ else None


_WANT = {1: ["찬성", "조건부", "중립", "반대"], -1: ["반대", "조건부", "중립", "찬성"], 0: ["중립", "조건부", "찬성", "반대"]}


def align_given(personas: list[Any], given: list[list[dict]], leans: list[float | None], cards_by: dict[str, dict],
                adapter: PersonaAdapter) -> list[list[dict]]:
    """기울기 맞춘 배분: 받는 사람·사람별 장수는 그대로, 관점·처지 조건 안에서 카드를 입장과 맞게 서로 바꾼다. 무작위 없음."""
    pool = [x for v in given for x in v if not x.get("hearsay_only")]
    out = [[x for x in v if x.get("hearsay_only")] for v in given]
    for i in sorted(range(len(personas)), key=lambda i: (leans[i] is None, i)):
        need = sum(1 for x in given[i] if not x.get("hearsay_only"))
        side = 0 if leans[i] is None else (1 if leans[i] > 0 else -1)
        for _ in range(need):
            ok = [x for x in pool if adapter.card_fits(cards_by[x["card"]], personas[i])]
            if not ok:
                break
            pick = min(ok, key=lambda x: (_WANT[side].index(cards_by[x["card"]]["stance_lean"]["lean"]), pool.index(x)))
            pool.remove(pick)
            out[i].append(pick)
    return out


def build_room(personas: list[Any], names: list[str], *, adapter: PersonaAdapter, digest: dict, target: dict,
               given: list[list[dict]], cards_by: dict[str, dict], leans: list[float | None], spec: dict | None = None,
               scene: Scene = KO, room_name: str | None = None, topic: TopicAdapter = GENERIC_KO,
               plugins: list | None = None) -> list[PersonPrompt]:
    """방 하나의 시민별 프롬프트. topic은 입장 문장·관계 칸 이름, plugins(PromptPlugin)는 칸·꼬리 추가."""
    spec = spec or load_spec()
    ctx = {"names": names, "target": target, "digest": digest, "topic": topic, "given": given}
    if spec.get("align_stance"):
        given = align_given(personas, given, leans, cards_by, adapter)
    out: list[PersonPrompt] = []
    for i, p in enumerate(personas):
        tier, head = topic.stance_line(leans[i])
        tail = head
        light = False
        if spec.get("light_support") and head and leans[i] > 0 and adapter.light_support_ok(p):
            tail = (tail + " " + spec["light_support"]).strip()
            light = True
        extras: list[str] = []
        lv = adapter.student_level(p)
        if spec.get("teen_rule") and lv:
            extras.append(spec["teen_rule"].format(level=lv))
        if spec.get("life_stage"):
            sl = adapter.stage_line(p)
            if sl:
                extras.append(spec.get("life_stage_label", "[내 처지]") + " " + sl + spec.get("life_stage_suffix", ""))
        if spec.get("relation") and target:
            rl = adapter.relation_line(p, target)
            if rl:
                extras.append(spec.get("relation_label", topic.relation_label) + " " + rl)
        if spec.get("self_reminder"):
            ss = adapter.short_self(p)
            if lv and spec.get("student_reminder"):
                tail = (tail + " " + spec["student_reminder"].format(level=lv)).strip()
            elif ss:
                tail = (tail + f" (너: {ss})").strip()
        if spec.get("living"):
            lv_ = adapter.living_line(p)
            if lv_:
                extras.append(spec.get("living_label", "[살림·동네]") + " " + lv_)
        if spec.get("known_label"):
            facts = digest.get("facts") or []
            if spec.get("known_trim") and not adapter.affected(p, target):
                facts = facts[: spec["known_trim"]]
            fl = []
            for f in facts:
                cond = f" ({f['condition']})" if spec.get("show_condition") and f.get("condition") else ""
                stt = f" [{f['status']}]" if spec.get("show_status") and f.get("status") else ""
                fl.append(spec.get("fact_fmt", "{statement}").format(statement=f.get("statement") or f.get("fact"), cond=cond, status=stt))
            jn = spec.get("known_join", " · ")
            extras.append(spec["known_label"] + (jn if jn.startswith("\n") else " ") + jn.join(fl) + spec.get("known_suffix", ""))
        if spec.get("unknown_label") and digest.get("not_stated"):
            extras.append(spec["unknown_label"] + " " + " · ".join(x.get("question", "") for x in digest["not_stated"])
                          + spec.get("unknown_suffix", ""))
        items = given[i]
        hs = []
        for x in items:
            pr = premise_of(cards_by[x["card"]])
            if pr and spec.get("hearsay_label"):
                hs.append(spec.get("hearsay_fmt", "{source}에서 본 얘기: {premise}").format(
                    source=src_phrase(cards_by[x["card"]]), premise=pr["premise"].rstrip("."),
                    scope=pr.get("scope", ""), time=pr.get("time", "")))
        hearsay = " / ".join(hs)
        if hs:
            extras.append(spec["hearsay_label"] + " " + hearsay + spec.get("hearsay_suffix", ""))
        own = [x for x in items if not x.get("hearsay_only")]
        if own and spec.get("interest_label"):
            parts = []
            for x in own:
                c = cards_by[x["card"]]
                fmt = spec["interest_fmt_link"] if spec.get("interest_fmt_link") and x.get("link") else spec.get("interest_fmt", "{interest}")
                parts.append(fmt.format(interest=c["interest"], ask=c.get("ask_form", ""), link=x.get("link", "")))
            extras.append(spec["interest_label"] + " " + " / ".join(parts) + spec.get("interest_suffix", ""))
        extras.extend(PL.sections(plugins, p, i, ctx))
        more = PL.tail(plugins, p, i, ctx)
        if more:
            tail = (tail + " " + more).strip()
        closing = spec.get("closing_nocard") if (spec.get("closing_nocard") and not own) else spec["closing"]
        system = system_message(names[i], adapter.fact_sections(p, target) + extras, spec.get("rule") or "",
                                scene=scene, room_name=room_name)
        out.append(PersonPrompt(system=system, before_closing=tail, closing=closing, stance_tier=tier,
                                light_support=light, hearsay=hearsay, cards=list(items)))
    return out
