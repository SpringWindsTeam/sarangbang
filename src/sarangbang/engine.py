"""단톡방 엔진 — 방 여러 개를 비동기로 돌린다(라운드 없음).

- 방마다 독립 상태(메시지·넘어감·마지막으로 물어본 때). 레인 슬롯은 방들이 함께 쓴다(레인별 전체 동시 한도).
- 발언 순위(urge): 정적 점수(어댑터가 데이터로 매김) + 최근 말함 감점 + 내 말에 온 답장 + 넘어감 감점 + 오래 안 물어봄.
  동점이면 앞 번호 — 무작위 없음(같은 입력·같은 응답이면 같은 순서).
- 한 시민당 진행 중 호출 1건. 늦게 도착한 답(본 뒤 새 메시지 > STALE_K)은 본 메시지에 답장 표시를 붙여 맥락을 지킨다.
- 앵커(정적 점수 상위 anchor_frac)는 앵커 레인, 나머지는 기본 레인. 앵커 레인 호출이 실패한 사람은 기본 레인으로 내린다.
- 방 종료: 메시지 target_msgs개 또는 연속 넘어감 2×인원.
매 호출은 system + user 두 메시지의 독립 호출이다(모델 쪽 기억 없음 — 대화 기록은 매번 user에 다시 렌더).
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from . import plugins as PL
from .log import render_log
from .reply import clean_reply
from .scene import KO, Scene
from .spec import PersonPrompt
from .topic import GENERIC_KO, TopicAdapter

logger = logging.getLogger(__name__)

STALE_K = 5
ANCHOR_FRAC = 6 / 36


class LaneLike(Protocol):
    label: str
    slots: int

    def call(self, messages: list[dict], max_tokens: int = 400) -> dict: ...


Scorer = Callable[[Any, dict], float]


@dataclass
class Room:
    room_id: str
    personas: list[Any]
    names: list[str]
    prompts: list[PersonPrompt]
    target: dict                     # 주제와 사람의 관계를 판단할 정보(예: 정책 대상 나이) — scorer에 그대로 넘긴다
    share: dict                      # {"author": 방 안 번호, "text": 첫 메시지}
    target_msgs: int = 100
    days: int = 1
    room_name: str = KO.room_name
    day_reset: bool = False          # 날이 바뀌면 대화 기록을 그날 것만(공유 #1은 남김)
    msgs: list[dict] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)
    scorer: Scorer | None = None     # (persona, target) → 정적 점수. 없으면 모두 0
    anchor_frac: float = ANCHOR_FRAC
    anchor_lane: str = "anchor"
    base_lane: str = "base"
    scene: Scene = KO
    topic: TopicAdapter = GENERIC_KO           # '이미 많이 나온 말'에서 뺄 주제 일반어(common_words)
    plugins: list = field(default_factory=list)  # PromptPlugin — call_context를 호출마다 넣는다

    def __post_init__(self):
        n = len(self.personas)
        self.passes = [0] * n
        self.last_asked = [0] * n
        self.consec_pass = 0
        self.static = [float(self.scorer(p, self.target)) if self.scorer else 0.0 for p in self.personas]
        self._init_static()
        if not self.msgs:
            self.msgs.append({"id": 1, "author": self.share["author"], "text": self.share["text"], "reply_to": None,
                              "vt": self.vt(0), "model": "공유", "seen_upto": 0, "stale": 0, "src": "share",
                              "call_id": 0, "reactions": [], "fixes": []})

    def _init_static(self) -> None:
        n = len(self.personas)
        order = sorted(range(n), key=lambda i: (-self.static[i], i))
        self.anchors = set(order[:max(1, round(n * self.anchor_frac))])
        self.lane_of = {i: (self.anchor_lane if i in self.anchors else self.base_lane) for i in range(n)}

    # ── 발언 순위 ──
    def urge(self, i: int) -> float:
        n = len(self.msgs)
        mine = [m for m in self.msgs if m["author"] == i]
        s = self.static[i] * 1.0
        if mine:
            since = n - mine[-1]["id"]
            s += -5 if since < 3 else (-2 if since < 8 else 0)
            my_ids = {m["id"] for m in mine}
            if any(m.get("reply_to") in my_ids and m["id"] > self.last_asked[i] for m in self.msgs):
                s += 4
        s -= self.passes[i] * 1.0
        s += (n - self.last_asked[i]) / 5.0  # 오래 안 물어본 사람은 앞으로
        return s

    def next_speaker(self, pool: list[int], busy) -> int | None:
        cands = [i for i in pool if i not in busy]
        if not cands:
            return None
        return max(cands, key=lambda i: (self.urge(i), -i))  # 동점이면 앞 번호(무작위 없음)

    def n_say(self) -> int:
        return len(self.msgs)

    def stopped(self) -> bool:
        return self.n_say() >= self.target_msgs or self.consec_pass >= 2 * len(self.personas)

    def stop_reason(self) -> str:
        return "target" if self.n_say() >= self.target_msgs else "quiet" if self.consec_pass >= 2 * len(self.personas) else "running"

    # ── 가상 시각: 하루 = target/days 메시지, 07:00~23:00에 고르게(메시지 수로 정해져 재현 가능) ──
    def vt(self, idx: int) -> dict:
        per_day = max(1, -(-self.target_msgs // max(1, self.days)))
        day, k = divmod(idx, per_day)
        minutes = 7 * 60 + int(16 * 60 * k / per_day)
        return {"day": day + 1, "time": f"{minutes // 60:02d}:{minutes % 60:02d}"}

    def user_message(self, i: int) -> str:
        pp = self.prompts[i]
        msgs = self.msgs
        if self.day_reset and len(msgs) > 1:
            today = self.vt(len(msgs))["day"]
            msgs = [m for m in msgs if m["id"] == 1 or (m.get("vt") or {}).get("day") == today]
        return render_log(msgs, self.names, i, len(self.personas), pp.closing, pp.before_closing,
                          scene=self.scene, room_name=self.room_name, common_words=self.topic.common_words,
                          context=PL.call_context(self.plugins, self, i))

    def inject(self, text: str) -> dict:
        """진행자 소식 — 대화 기록에 '#n 알림: …'으로 보인다(발언자 없음)."""
        m = {"id": len(self.msgs) + 1, "author": -1, "kind": "inject", "text": text, "reply_to": None,
             "vt": self.vt(len(self.msgs)), "model": "", "seen_upto": len(self.msgs), "stale": 0, "src": "inject",
             "call_id": 0, "reactions": [], "fixes": []}
        self.msgs.append(m)
        return m

    def apply(self, i: int, kind: str, args: dict, seen_upto: int, model: str, call_id: int) -> dict | None:
        if kind == "say":
            reply_to = args.get("reply_to") or 0
            if reply_to and not any(m["id"] == reply_to for m in self.msgs):
                reply_to = 0
            stale = len(self.msgs) - seen_upto
            auto_reply = False
            if stale > STALE_K and not reply_to and seen_upto:
                reply_to, auto_reply = seen_upto, True
            m = {"id": len(self.msgs) + 1, "author": i, "text": args["text"].strip(), "reply_to": reply_to or None,
                 "auto_reply": auto_reply, "vt": self.vt(len(self.msgs)), "model": model, "seen_upto": seen_upto,
                 "stale": stale, "src": "text", "call_id": call_id, "reactions": [], "fixes": args.get("fixes", [])}
            self.msgs.append(m)
            self.consec_pass = 0
            return m
        self.passes[i] += 1
        self.consec_pass += 1
        return None


def parse_text(res: dict, self_name: str, all_names: list[str]) -> tuple[str, dict]:
    """텍스트 모드 응답 → ('say'|'pass'|'error', args)."""
    if not res.get("ok"):
        return "error", {}
    text, reply, is_pass, fixes = clean_reply(res.get("content") or "", self_name, all_names)
    if is_pass:
        return "pass", {"fixes": fixes}
    return "say", {"text": text, "reply_to": reply or 0, "fixes": fixes}


OnMessage = Callable[[Room, dict], "Awaitable[None] | None"]


async def run_rooms(rooms: list[Room], lanes: dict[str, LaneLike], *, on_message: OnMessage | None = None,
                    should_cancel: Callable[[], bool] | None = None, poll: float = 0.5) -> dict:
    """방들을 끝까지 돌린다. 방의 앵커 레인이 lanes에 없으면 그 방은 모두 기본 레인. 결과: 방별 종료 사유·시간·호출 수."""
    for r in rooms:
        if r.anchor_lane not in lanes:
            r.lane_of = {i: r.base_lane for i in r.lane_of}
    busy: dict[tuple[int, int], asyncio.Task] = {}
    call_seq = [0]
    t0 = time.time()

    async def call(r: Room, i: int, lane: LaneLike, user: str) -> tuple[int, dict]:
        call_seq[0] += 1
        cid = call_seq[0]
        msgs = [{"role": "system", "content": r.prompts[i].system}, {"role": "user", "content": user}]
        return cid, await asyncio.to_thread(lane.call, msgs)

    def used(lane_name: str) -> int:
        return sum(1 for (ri, i) in busy if rooms[ri].lane_of[i] == lane_name)

    while True:
        if should_cancel and should_cancel():
            break
        live = [ri for ri, r in enumerate(rooms) if not r.stopped()]
        if not live and not busy:
            break
        for lname, lane in lanes.items():
            k = used(lname)
            stuck = False
            while k < lane.slots and not stuck:
                stuck = True
                # 진행이 덜 된 방부터(방들이 고르게 나아가게) — 동점이면 방 번호 순
                for ri in sorted(live, key=lambda ri: (rooms[ri].n_say() / max(1, rooms[ri].target_msgs), ri)):
                    r = rooms[ri]
                    pool = [j for j in range(len(r.personas)) if r.lane_of[j] == lname]
                    who = r.next_speaker(pool, {i for (rj, i) in busy if rj == ri})
                    if who is None:
                        continue
                    seen = r.n_say()
                    u = r.user_message(who)
                    r.last_asked[who] = seen
                    t = asyncio.create_task(call(r, who, lane, u))
                    t.meta = (lname, seen, u)  # type: ignore[attr-defined]
                    busy[(ri, who)] = t
                    k += 1
                    stuck = False
                    break
        if not busy:
            break
        done, _ = await asyncio.wait(busy.values(), timeout=poll, return_when=asyncio.FIRST_COMPLETED)
        for key, task in list(busy.items()):
            if task not in done:
                continue
            ri, who = key
            r = rooms[ri]
            lname, seen, u = task.meta  # type: ignore[attr-defined]
            del busy[key]
            try:
                cid, res = task.result()
            except Exception as e:  # noqa: BLE001 — 한 호출 실패가 방을 멈추지 않게
                cid, res = 0, {"ok": False, "error": str(e)[:200]}
            kind, args = parse_text(res, r.names[who], r.names)
            if lname == r.anchor_lane and not res.get("ok") and r.base_lane in lanes:
                r.lane_of[who] = r.base_lane  # 앵커 레인 실패 → 기본 레인으로 내림
            m = None
            if not r.stopped():
                m = r.apply(who, kind, args, seen, lanes[lname].label, cid)
            r.calls.append({"call_id": cid, "who": who, "lane": lname, "seen_upto": seen, "kind": kind,
                            "msg_id": m["id"] if m else None, "latency": res.get("latency"), "ok": bool(res.get("ok")),
                            "error": res.get("error"), "raw": res.get("content"), "fixes": args.get("fixes", []),
                            "t": round(time.time() - t0, 2)})
            if m and on_message:
                rv = on_message(r, m)
                if asyncio.iscoroutine(rv):
                    await rv
    for task in busy.values():  # 취소 시 남은 호출은 버린다
        task.cancel()
    return {"sec": round(time.time() - t0, 1), "calls": call_seq[0],
            "rooms": [{"room_id": r.room_id, "messages": r.n_say(), "stop": r.stop_reason()} for r in rooms]}
