"""sarangbang 빠른 시작 — 내장 시나리오(동네 도서관 야간 개관 · 시민 4명 · 카드 4장)로 방 하나를 돌린다.

    python examples/quickstart.py --fake                 # 네트워크 없이(정해 둔 답으로) 흐름만 확인
    python examples/quickstart.py --fake --topic policy  # 정책 주제 문구(ko_s12)로
    SARANGBANG_PROVIDER=upstage UPSTAGE_API_KEY=… python examples/quickstart.py --msgs 30
    SARANGBANG_BASE_URL=http://localhost:8000/v1 SARANGBANG_MODEL=skt/A.X-4.0-Light python examples/quickstart.py

같은 일을 `sarangbang quickstart --fake` 명령으로도 할 수 있다. 이 파일은 라이브러리 API를 직접 쓰는 본보기다.
실제 모델이면 첫 메시지도 LLM(material.seed_message)이 쓴다. --fake면 고정 문장.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from sarangbang import json_llm_from_env, lane_from_env, load_scenario, run_rooms
from sarangbang import scenario as S


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--msgs", type=int, default=20)
    ap.add_argument("--topic", choices=["generic", "policy"], default="generic", help="주제 문구: 범용 소식 | 정책(ko_s12)")
    a = ap.parse_args()

    d = load_scenario("toy_library")                 # 또는 load_scenario("my_scenario.json")
    prep = S.prepare(d, topic=a.topic)               # 카드 배분 → 시민별 프롬프트(LLM 없음)
    if a.fake:
        lanes = {"base": S.fake_lane(slots=2)}
        share = S.seed_share(d, prep, None)          # 고정 첫 메시지
    else:
        lanes = {"base": lane_from_env("base")}      # SARANGBANG_PROVIDER 또는 SARANGBANG_BASE_URL·API_KEY·MODEL
        share = S.seed_share(d, prep, json_llm_from_env())
    room = S.make_room(d, prep, share, target_msgs=a.msgs)

    print(S.format_line(room, room.msgs[0]))
    stats = asyncio.run(run_rooms([room], lanes, on_message=lambda r, m: print(S.format_line(r, m))))
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
