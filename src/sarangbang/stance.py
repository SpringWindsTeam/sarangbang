"""입장 문장 — 시민별 입장 기울기(-1~1)를 user 꼬리 머리 문장으로. 문구와 경계는 주제 어댑터(topic.Topic)가 정한다.

기울기를 어떻게 계산할지는 쓰는 쪽 몫이다(예: 신념·이해관계 판단 모델). 엔진은 기울기 숫자만 받는다.
"""
from __future__ import annotations

from .topic import GENERIC_KO, TopicAdapter


def stance_line(lv: float | None, topic: TopicAdapter = GENERIC_KO) -> tuple[str, str]:
    """(등급, 머리 문장). 등급: 강찬·강반·중찬·중반·약찬·약반·없음(입장 없음은 빈 문장)."""
    return topic.stance_line(lv)
