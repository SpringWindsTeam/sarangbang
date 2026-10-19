"""Nemotron-Personas-Korea(증강판) 어댑터 — 데이터셋 한 행(dict)을 그대로 시민 레코드로 쓴다.

데이터셋: https://huggingface.co/datasets/springwindteam/nemotron-personas-korea-augmented (CC BY 4.0,
NVIDIA Nemotron-Personas-Korea 파생). 만 19세 이상 합성 한국인 100만 명, 행마다 인구통계·직업·가구·서사 열.

쓰는 열: sex, age, province, district, occupation, education_level, marital_status, family_type, housing_type,
income_rank, has_children, is_education_worker, activity_status, mc_household, persona, story_summary.
자녀 나이·성격 점수 열은 없다 — [우리 아이]는 자녀 유무만, 성격은 넣지 않는다(서사를 켜면 서사로 대신).

주제와의 관계(relation_line·affected·static_score)는 `target["relations"]` 규칙으로 정한다(데이터 열 조건 → 문장).

    target = {"relations": [
        {"if": {"has_children": True}, "text": "자녀가 있어 아이들 일에 관심이 많다", "score": 2},
        {"if": {"is_education_worker": True}, "text": "교육 분야에서 일한다", "score": 3},
        {"if": {"province": ["서울", "경기"]}, "text": "수도권에 산다", "score": 1},
    ]}

조건 값이 목록이면 그중 하나와 같으면 맞다. 맞는 규칙들의 문장을 ' · '로 잇고 점수를 더한다. 무작위는 없다.
"""
from __future__ import annotations

import re
from typing import Any

_PROVINCE_FULL = {"충청북": "충북", "충청남": "충남", "전라북": "전북", "전라남": "전남", "경상북": "경북", "경상남": "경남"}


def _prov(p: dict) -> str:
    v = str(p.get("province") or "")
    return _PROVINCE_FULL.get(v, v)


def _place(p: dict) -> str:
    """'인천-연수구' → '인천 연수구', '경기-용인시 처인구' → '경기 용인시 처인구'."""
    d = str(p.get("district") or "")
    return d.replace("-", " ") if d else _prov(p)


def _match(p: dict, cond: dict) -> bool:
    for k, want in cond.items():
        v = p.get(k)
        if isinstance(want, (list, tuple, set)):
            if v not in want:
                return False
        elif v != want:
            return False
    return True


class NemotronKoreaAdapter:
    """include_story=True면 [내 이야기]에 story_summary(1인칭 ~100자)를 넣는다. 기본은 끔 — 한국어 모델 실험에서
    서사를 통째로 넣으면 대화 주제와 무관한 자기소개·서사 문구 복사가 늘었다(필요하면 비교한 뒤 켤 것)."""

    STUDENT = "재학"

    def __init__(self, include_story: bool = False, story_label: str = "[내 이야기]"):
        self.include_story = include_story
        self.story_label = story_label

    # ── 사실 섹션 ──
    def me_line(self, p: dict) -> str:
        occ = str(p.get("occupation") or "")
        act = str(p.get("activity_status") or "")
        work = act if (not occ or occ == "무직") and act and act != "재직" else occ
        parts = [f"{p.get('age')}세 {p.get('sex') or ''}".strip(), f"{_place(p)}에 산다"]
        if work:
            parts.append(work)
        if p.get("education_level"):
            parts.append(f"학력 {p['education_level']}")
        if p.get("mc_household"):
            parts.append("다문화 가구")
        return " · ".join(parts)

    def fact_sections(self, p: dict, target: dict) -> list[str]:
        out = [f"[나] {self.me_line(p)}"]
        if p.get("has_children"):
            out.append("[우리 아이] 자녀가 있다")
        if self.include_story and p.get("story_summary"):
            out.append(f"{self.story_label} {p['story_summary']}")
        return out

    def student_level(self, p: dict) -> str:
        return "대학생" if p.get("activity_status") == self.STUDENT else ""

    def stage_line(self, p: dict) -> str:
        bits = [str(p.get(k)) for k in ("marital_status", "family_type") if p.get(k)]
        return " · ".join(dict.fromkeys(bits))

    def _rules(self, p: dict, target: dict) -> list[dict]:
        return [r for r in (target or {}).get("relations") or [] if _match(p, r.get("if") or {})]

    def relation_line(self, p: dict, target: dict) -> str:
        return " · ".join(r["text"] for r in self._rules(p, target) if r.get("text"))

    def short_self(self, p: dict) -> str:
        bits = [f"{p.get('age')}세", str(p.get("occupation") or p.get("activity_status") or "")]
        if p.get("family_type") == "혼자 거주":
            bits.append("혼자 산다")
        return " · ".join(b for b in bits if b and b != "무직")

    def living_line(self, p: dict) -> str:
        bits = [str(p.get("housing_type") or "")]
        if p.get("income_rank"):
            bits.append(f"소득 {p['income_rank']}")
        return " · ".join(b for b in bits if b)

    def affected(self, p: dict, target: dict) -> bool:
        """target["relations"] 규칙 중 하나라도 맞으면 직접 영향권."""
        return bool(self._rules(p, target))

    def light_support_ok(self, p: dict) -> bool:
        return True

    # ── 카드 ──
    def tags(self, p: dict) -> set[str]:
        t = set()
        if p.get("has_children"):
            t |= {"parent", "any_kid"}
        if p.get("is_education_worker"):
            t.add("edu_worker")
        if p.get("activity_status") == self.STUDENT:
            t.add("student")
        if p.get("mc_household"):
            t.add("multicultural")
        if p.get("activity_status") in ("재직",):
            t.add("worker")
        return t

    def card_fits(self, card: dict, p: dict) -> bool:
        return all(r in self.tags(p) for r in card.get("require") or [])

    def own_perspectives(self, p: dict) -> list[str]:
        t = self.tags(p)
        return [name for name, need in (("학부모", "parent"), ("교사·돌봄 인력", "edu_worker"), ("학생", "student")) if need in t]

    def static_score(self, p: dict, target: dict) -> float:
        return float(sum(r.get("score", 1) for r in self._rules(p, target)))

    def seed_profile(self, p: dict, target: dict) -> list[str]:
        return [self.me_line(p), "우리 아이: " + ("자녀가 있다" if p.get("has_children") else "자녀 없음"),
                self.stage_line(p), self.relation_line(p, target)]

    def display_names(self, personas: list[Any]) -> list[str]:
        """사는 곳 끝 낱말('연수구'→'연수')을 이름으로 — 나이·성별을 이름에 넣으면 자기소개가 늘었다. 겹치면 시도를 앞에, 그래도 겹치면 번호."""
        def short(w: str) -> str:
            t = re.sub(r"(특별자치시|광역시|특별시|시|군|구)$", "", w)
            return t if len(t) >= 2 else w
        base = [short(_place(p).split()[-1]) if _place(p) else "이웃" for p in personas]
        out: list[str] = []
        for i, n in enumerate(base):
            if base.count(n) > 1:
                n = f"{_prov(personas[i])} {n}"
            k, cand = 2, n
            while cand in out:
                cand, k = f"{n}{k}", k + 1
            out.append(cand)
        return out
