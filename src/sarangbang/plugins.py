"""프롬프트 주입 인터페이스(PromptPlugin) — 사양 JSON 밖에서 프롬프트를 더 넣는 자리.

끼어드는 곳은 세 군데다. 필요한 메서드만 구현하면 된다(없는 메서드는 건너뛴다).

| 메서드 | 언제 | 어디에 |
|---|---|---|
| system_sections(p, i, ctx) → list[str] | 방 준비 때 한 번(build_room) | system의 사양 칸 뒤, 공통 규칙 앞 |
| tail(p, i, ctx) → str | 방 준비 때 한 번(build_room) | user의 마무리 앞 꼬리(before_closing) 끝 |
| call_context(room, i) → str | 호출할 때마다(Room.user_message) | user의 대화 기록과 마무리 앞 꼬리 사이 |

ctx는 {"names", "target", "digest", "topic", "given"}이다. call_context는 대화 진행에 따라 바뀌는 지시(예: 지금 시각·
날씨, 방금 들어온 소식에 대한 개인 반응 유도)를 넣을 때 쓴다. 매 호출이 독립이라 여기서 넣은 문맥은 그 호출에만 들어간다.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PromptPlugin(Protocol):
    """모든 메서드가 선택이다 — 쓰는 지점만 구현한다."""


def sections(plugins, p: Any, i: int, ctx: dict) -> list[str]:
    out: list[str] = []
    for pl in plugins or ():
        f = getattr(pl, "system_sections", None)
        if f:
            out.extend(x for x in f(p, i, ctx) or [] if x)
    return out


def tail(plugins, p: Any, i: int, ctx: dict) -> str:
    parts = []
    for pl in plugins or ():
        f = getattr(pl, "tail", None)
        if f:
            t = f(p, i, ctx)
            if t:
                parts.append(t)
    return " ".join(parts)


def call_context(plugins, room: Any, i: int) -> str:
    parts = []
    for pl in plugins or ():
        f = getattr(pl, "call_context", None)
        if f:
            t = f(room, i)
            if t:
                parts.append(t)
    return "\n".join(parts)


class StaticSections:
    """모든 시민(또는 who(p, i)가 참인 시민)에게 같은 칸을 붙이는 간단한 플러그인."""

    def __init__(self, sections: list[str], who=None):
        self.items, self.who = list(sections), who

    def system_sections(self, p: Any, i: int, ctx: dict) -> list[str]:
        return self.items if (self.who is None or self.who(p, i)) else []
