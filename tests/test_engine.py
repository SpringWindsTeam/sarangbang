import asyncio
import itertools

from sarangbang import DictAdapter, FakeLane, PersonPrompt, Room, render_log, run_rooms


def _room(n=4, target_msgs=12, **kw):
    ps = [{"name": f"p{i}", "score": s} for i, s in enumerate([3, 1, 2, 0][:n])]
    prompts = [PersonPrompt(system=f"sys{i}", before_closing="", closing="말해") for i in range(n)]
    return Room("r1", ps, [p["name"] for p in ps], prompts, {}, {"author": 0, "text": "소식이요"},
                target_msgs=target_msgs, days=2, scorer=DictAdapter().static_score, **kw)


def test_static_and_anchor():
    r = _room()
    assert r.static == [3.0, 1.0, 2.0, 0.0]
    assert r.anchors == {0}
    assert r.lane_of[0] == "anchor" and r.lane_of[1] == "base"


def test_run_reaches_target_deterministically():
    def go():
        lines = itertools.cycle(["좋아요", "(#1에 답장) 그러게요", "(넘어감)", "걱정돼요"])
        r = _room()
        asyncio.run(run_rooms([r], {"base": FakeLane("base", lambda m: next(lines), slots=1)}, poll=0.01))
        return [(m["author"], m["text"], m["reply_to"]) for m in r.msgs], r.stop_reason()
    a, b = go(), go()
    assert a == b
    assert a[1] == "target" and len(a[0]) == 12


def test_quiet_stop():
    r = _room(target_msgs=50)
    asyncio.run(run_rooms([r], {"base": FakeLane("base", lambda m: "(넘어감)")}, poll=0.01))
    assert r.stop_reason() == "quiet" and r.n_say() == 1


def test_vt_and_day_reset():
    r = _room(target_msgs=4, day_reset=True)
    for k in range(2):
        r.apply(1, "say", {"text": f"말{k}"}, r.n_say(), "fake", k + 1)
    assert [m["vt"]["day"] for m in r.msgs] == [1, 1, 2]
    u = r.user_message(2)          # 다음 메시지는 2일차 — 2일차 대화(#3)와 공유 #1만 보인다
    assert "#1 " in u and "#2 " not in u and "#3 " in u


def test_render_log_window_keeps_share_and_mine():
    msgs = [{"id": 1, "author": 0, "text": "공유"}] + [{"id": i, "author": 1 + (i % 2), "text": f"m{i}"} for i in range(2, 50)]
    msgs[3]["author"] = 3   # id 4는 '나'
    out = render_log(msgs, ["a", "b", "c", "d"], 3, 4, "끝", window=5)
    assert "#1 a: 공유" in out and "#4 나: m4" in out and "#49 " in out and "#20 " not in out
    assert out.endswith("끝")
