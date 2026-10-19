"""주제 어댑터(Topic) — 시민들이 무엇을 두고 이야기하는지에 따라 바뀌는 문구를 한곳에 모은다.

엔진·카드 배분·대화 기록은 주제와 무관하다. 주제가 정하는 것은 다음뿐이다.
- noun·label: 주제를 부르는 낱말과 사실 머리표(예: '정책' · '[정책]')
- stance_heads: 입장 기울기 등급별 머리 문장(user 꼬리)
- relation_label: 사람과 주제의 관계 칸 이름(예: '[이 정책과 나]')
- relevance_system · link_system · seed_system: 재료 준비 프롬프트(카드 관련성 · 연결 의견 · 첫 메시지)
- common_words: '이미 많이 나온 말'에서 뺄 주제 일반어

`POLICY_KO`는 한국어 교육정책 시뮬레이션에서 비교 시험으로 고른 문구, `GENERIC_KO`는 정책이 아닌 소식(가게·동네·회사·제품 등)용
범용 문구다(시험 전). 자기 주제는 `dataclasses.replace(GENERIC_KO, …)`나 `Topic(…)`으로 만든다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

TIERS = ("강찬", "강반", "중찬", "중반", "약찬", "약반")


@runtime_checkable
class TopicAdapter(Protocol):
    noun: str
    relation_label: str
    relevance_system: str
    link_system: str
    seed_system: str
    common_words: frozenset[str]

    def head(self, title: str, digest: dict) -> str:
        """카드 판정·연결 의견·첫 메시지 호출에 붙이는 주제 머리(이름 + 요약 + 사실 목록)."""

    def stance_line(self, lv: float | None) -> tuple[str, str]:
        """입장 기울기(-1~1) → (등급, user 꼬리 머리 문장). 입장 없음은 ('없음', '')."""


@dataclass(frozen=True)
class Topic:
    noun: str
    label: str                                   # 사실 머리표(예: '[정책]')
    stance_heads: dict[str, str]                 # TIERS 키마다 머리 문장
    relation_label: str
    relevance_system: str
    link_system: str
    seed_system: str
    common_words: frozenset[str] = field(default_factory=frozenset)
    strong: float = 0.6                          # 등급 경계: |기울기| ≥ strong → 강, ≥ mid → 중, ≥ weak → 약, 그 밖은 없음
    mid: float = 0.3
    weak: float = 0.05

    def head(self, title: str, digest: dict) -> str:
        return f"{self.label} {title}\n{digest.get('summary', '')}\n" + "\n".join(
            f"- {f.get('statement') or f.get('fact')}" for f in digest.get("facts") or [])

    def tier(self, lv: float | None) -> str:
        if lv is None or abs(lv) < self.weak:
            return "없음"
        mag = abs(lv)
        return ("강" if mag >= self.strong else "중" if mag >= self.mid else "약") + ("찬" if lv > 0 else "반")

    def stance_line(self, lv: float | None) -> tuple[str, str]:
        t = self.tier(lv)
        return (t, "" if t == "없음" else self.stance_heads[t])


POLICY_KO = Topic(
    noun="정책",
    label="[정책]",
    stance_heads={
        "강찬": "당신은 이런 정책이 꼭 필요하다고 믿어 온 사람이다.",
        "강반": "당신은 이런 정책이 잘못됐다고 믿어 온 사람이다.",
        "중찬": "당신은 이런 정책에 대체로 찬성해 온 사람이다.",
        "중반": "당신은 이런 정책에 대체로 회의적이었던 사람이다.",
        "약찬": "당신은 이런 정책을 반기는 편이다.",
        "약반": "당신은 이런 정책이 미덥지 않은 편이다.",
    },
    relation_label="[이 정책과 나]",
    relevance_system="""너는 시민 대화 시뮬레이션 준비를 돕는 보조다. 정책 하나와 여론 쟁점 카드 목록(이름·주장·원글 제목)이 주어진다.
이 정책을 두고 시민들이 단톡방에서 이야기할 때 그 쟁점이 자연스럽게 나올 수 있는지 판정한다.
- direct: 이 정책의 내용·대상·운영을 직접 두고 나오는 쟁점
- related: 이 정책 얘기를 하다 자연스럽게 넘어가는 쟁점 — 이 정책이 그 문제에 실제로 영향을 주거나, 같은 대상이 같은 시기에 겪는 일
- unrelated: 위 둘이 아님. 같은 '학교 생활'·'교육' 영역이라는 이유만으로는 related가 아니다(예: 돌봄 정책 얘기에 학교폭력 신고 절차, 입시 면접 요령은 unrelated)
JSON으로만: {"labels":[{"i":번호,"rel":"direct|related|unrelated"}]} — 모든 번호에 하나씩.""",
    link_system="""너는 시민 대화 시뮬레이션 준비를 돕는 보조다. 정책 하나와, 이 정책 얘기에서 나올 쟁점 카드들이 주어진다.
카드마다 그 쟁점을 가진 시민이 '이 정책과 이 쟁점을 어떻게 잇는지'를 1인칭 의견 한 줄(25~50자)로 쓴다.
사실로 단정하지 말고 생각·짐작·걱정으로 쓴다(예: '늘봄으로 초등 교사 수요가 늘면 교대 가는 게 나아질지도 모르겠다').
JSON으로만: {"links":[{"i":번호,"link":"..."}]}""",
    seed_system="""너는 단톡방 시뮬레이션 준비를 돕는 보조다. 정책 요약·사실 목록과, 이 소식을 단톡방에 처음 올리는 사람에 대한 사실이 주어진다.
그 사람이 단톡방에 올릴 첫 메시지를 한두 문장으로 쓴다.
- 앞 문장: 정책 사실 한 가지를 '~한다네요~^^'처럼 가볍게 전한다. 사실은 목록에 있는 것만, 숫자는 그대로.
- 뒷 문장: 그 사람에 대한 사실에 비추어 반가운 마음을 한마디 붙인다.
- 가족·직업·경험은 [그 사람에 대한 사실]에 적힌 것만 말한다. 자녀가 없으면 자녀 얘기를 하지 않고, 적혀 있지 않은 조카·형제·손주를 만들지 않는다.
JSON으로만: {"text":"첫 메시지"}""",
    common_words=frozenset({"정책", "제도", "확대", "확대되", "지원"}),
)

GENERIC_KO = Topic(
    noun="소식",
    label="[소식]",
    stance_heads={
        "강찬": "당신은 이 일이 꼭 있어야 한다고 생각해 온 사람이다.",
        "강반": "당신은 이 일이 잘못됐다고 생각해 온 사람이다.",
        "중찬": "당신은 이 일을 대체로 좋게 보는 사람이다.",
        "중반": "당신은 이 일을 대체로 못마땅하게 보는 사람이다.",
        "약찬": "당신은 이 일을 반기는 편이다.",
        "약반": "당신은 이 일이 미덥지 않은 편이다.",
    },
    relation_label="[이 일과 나]",
    relevance_system="""너는 대화 시뮬레이션 준비를 돕는 보조다. 소식 하나와 쟁점 카드 목록(이름·주장·원글 제목)이 주어진다.
이 소식을 두고 사람들이 단톡방에서 이야기할 때 그 쟁점이 자연스럽게 나올 수 있는지 판정한다.
- direct: 이 소식의 내용·대상·방식을 직접 두고 나오는 쟁점
- related: 이 소식 얘기를 하다 자연스럽게 넘어가는 쟁점 — 이 소식이 그 문제에 실제로 영향을 주거나, 같은 사람들이 같은 시기에 겪는 일
- unrelated: 위 둘이 아님. 같은 분야라는 이유만으로는 related가 아니다
JSON으로만: {"labels":[{"i":번호,"rel":"direct|related|unrelated"}]} — 모든 번호에 하나씩.""",
    link_system="""너는 대화 시뮬레이션 준비를 돕는 보조다. 소식 하나와, 이 소식 얘기에서 나올 쟁점 카드들이 주어진다.
카드마다 그 쟁점을 가진 사람이 '이 소식과 이 쟁점을 어떻게 잇는지'를 1인칭 의견 한 줄(25~50자)로 쓴다.
사실로 단정하지 말고 생각·짐작·걱정으로 쓴다.
JSON으로만: {"links":[{"i":번호,"link":"..."}]}""",
    seed_system="""너는 단톡방 시뮬레이션 준비를 돕는 보조다. 소식 요약·사실 목록과, 이 소식을 단톡방에 처음 올리는 사람에 대한 사실이 주어진다.
그 사람이 단톡방에 올릴 첫 메시지를 한두 문장으로 쓴다.
- 앞 문장: 사실 한 가지를 '~한다네요'처럼 가볍게 전한다. 사실은 목록에 있는 것만, 숫자는 그대로.
- 뒷 문장: 그 사람에 대한 사실에 비추어 느낀 점을 한마디 붙인다.
- 가족·직업·경험은 [그 사람에 대한 사실]에 적힌 것만 말한다. 적혀 있지 않은 가족·지인을 만들지 않는다.
JSON으로만: {"text":"첫 메시지"}""",
    common_words=frozenset({"소식", "이번", "얘기"}),
)
