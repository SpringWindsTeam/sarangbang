"""페르소나 어댑터 — 엔진·프롬프트 조립이 시민 레코드에서 읽는 것을 한곳에 모은 인터페이스.

sarangbang은 시민 레코드의 모양을 정하지 않는다. 레코드(dict든 무엇이든)를 그대로 넘기고, 어댑터가 문장·판정을 만든다.
`DictAdapter`는 미리 문장으로 적어 둔 간단한 dict 레코드용 기본 구현이다(예제·시험).
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PersonaAdapter(Protocol):
    def fact_sections(self, p: Any, target: dict) -> list[str]:
        """system 앞부분 사실 섹션(예: ['[나] …', '[우리 아이] …', '[내 성격] …'])."""
    def student_level(self, p: Any) -> str:
        """학생이면 학년 표기(예: '고2'), 아니면 ''."""
    def stage_line(self, p: Any) -> str:
        """[내 처지] 한 줄(없으면 '')."""
    def relation_line(self, p: Any, target: dict) -> str:
        """관계 칸(topic.relation_label, 예: [이 정책과 나]) 한 줄 — 주제와 이 사람의 관계(없으면 '')."""
    def short_self(self, p: Any) -> str:
        """user 꼬리의 신상 요약 '(너: …)' 안쪽(없으면 '')."""
    def living_line(self, p: Any) -> str:
        """[살림·동네] 한 줄(없으면 '')."""
    def affected(self, p: Any, target: dict) -> bool:
        """주제의 직접 영향권인가 — 아니면 [알고 있는 것]을 사양의 known_trim개로 줄인다."""
    def light_support_ok(self, p: Any) -> bool:
        """찬성 쪽 시민에게 '가벼운 찬성' 꼬리를 붙여도 되는가(예: 성실성이 높은 사람은 제외)."""
    def card_fits(self, card: dict, p: Any) -> bool:
        """이 쟁점 카드를 이 사람이 자기 관심사로 가져도 되는가(관점·필수 처지)."""
    def own_perspectives(self, p: Any) -> list[str]:
        """이 사람 자신의 관점 이름(카드 perspective와 같은 낱말) — 배분 때 자기 관점 카드를 먼저 준다."""
    def static_score(self, p: Any, target: dict) -> float:
        """발언 순위의 정적 점수(높을수록 먼저·자주). 상위 일부가 앵커 레인을 쓴다."""
    def seed_profile(self, p: Any, target: dict) -> list[str]:
        """첫 메시지를 올리는 사람에 대한 사실 줄."""
    def display_names(self, personas: list[Any]) -> list[str]:
        """방 안 표시 이름(겹치지 않게)."""


class DictAdapter:
    """간단한 dict 레코드용 어댑터 — 필드를 문장으로 미리 적어 둔다.

    레코드 필드(모두 선택): name, me, kids, personality, values, stage, relation, short_self, living,
    student_level, affected(bool), perspectives(list), situation(list), steady(bool: 가벼운 찬성 제외), score(float)."""

    def fact_sections(self, p: dict, target: dict) -> list[str]:
        out = [f"[나] {p.get('me', '')}"]
        for label, k in (("[우리 아이]", "kids"), ("[내 성격]", "personality"), ("[내 가치관]", "values")):
            if p.get(k):
                out.append(f"{label} {p[k]}")
        return out

    def student_level(self, p: dict) -> str:
        return p.get("student_level", "")

    def stage_line(self, p: dict) -> str:
        return p.get("stage", "")

    def relation_line(self, p: dict, target: dict) -> str:
        return p.get("relation", "")

    def short_self(self, p: dict) -> str:
        return p.get("short_self", "")

    def living_line(self, p: dict) -> str:
        return p.get("living", "")

    def affected(self, p: dict, target: dict) -> bool:
        return bool(p.get("affected", True))

    def light_support_ok(self, p: dict) -> bool:
        return not p.get("steady", False)

    def card_fits(self, card: dict, p: dict) -> bool:
        need = card.get("require") or []
        return all(r in (p.get("situation") or []) for r in need)

    def own_perspectives(self, p: dict) -> list[str]:
        return list(p.get("perspectives") or [])

    def static_score(self, p: dict, target: dict) -> float:
        return float(p.get("score", 0))

    def seed_profile(self, p: dict, target: dict) -> list[str]:
        return [x for x in (p.get("me", ""), p.get("kids", ""), p.get("stage", ""), p.get("relation", "")) if x]

    def display_names(self, personas: list[dict]) -> list[str]:
        return [p.get("name") or f"참여자{i + 1}" for i, p in enumerate(personas)]
