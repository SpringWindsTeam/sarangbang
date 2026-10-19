"""장면(Scene) — 단톡방 이름·설명·공통 규칙·대화 기록 창 크기·화면 낱말. 기본값은 한국어 단톡방(ko).

문구는 비교 시험으로 고른 것이다. 바꾸면 같은 판정으로 다시 시험할 것.
"""
from __future__ import annotations

from dataclasses import dataclass, field

KO_JOSA = ("에서는", "으로는", "에서도", "이라고", "에게서", "까지는", "부터는", "에서", "으로", "에게", "까지", "부터", "처럼",
           "보다", "이라", "라고", "하고", "이랑", "랑", "은", "는", "이", "가", "을", "를", "에", "의", "도", "로", "과", "와", "만")
# '이미 많이 나온 말' 판정에서 빼는 한국어 일반어. 주제 일반어(정책·제도 등)는 Topic.common_words가 더한다.
KO_SAT_STOP = frozenset(["우리", "동네", "걱정", "생각", "마음", "소식", "말씀", "부분", "문제", "사람", "필요", "현실", "정말", "이번", "지금", "그래도", "결국", "반갑", "다행", "같은", "저도", "저는", "그런", "이런", "있다", "없다", "하는", "되는", "것", "같아요", "같아", "있어요", "해요"])


@dataclass(frozen=True)
class Scene:
    room_name: str = "소소한 이야기방"
    room_desc: str = "몇 년째 같은 온라인 카페에서 알고 지낸 사람들이 모인 단톡방이라 서로 편하게 이야기한다"
    rules: str = ("단톡방에서 실제로 할 말만 쓴다. 한두 문장.\n"
                  "다른 사람이 한 말을 그대로 따라 하지 않는다.\n"
                  "위 사실에 없는 가족·직업·경험을 지어내지 않는다.\n"
                  "할 말이 없으면 넘어간다.")
    window: int = 30                  # 대화 기록에 보여 줄 최근 메시지 수(공유 #1·내 말·내게 온 답장은 창 밖이어도 남김)
    me: str = "나"
    notice: str = "알림"              # 진행자가 넣은 소식(kind=inject)의 화자 이름
    gap: str = "   …(이전 대화 생략)…"
    josa: tuple[str, ...] = KO_JOSA
    sat_stop: frozenset[str] = field(default_factory=lambda: KO_SAT_STOP)

    def header(self, n_members: int) -> str:
        return f"[{self.room_name} · {n_members}명]"

    def intro(self, name: str) -> str:
        return f"너는 '{self.room_name}' 단톡방에 있는 '{name}'이다. 이 방은 {self.room_desc}.\n아래는 너에 대한 사실이다.\n\n"


KO = Scene()
