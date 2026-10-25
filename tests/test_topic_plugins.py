import asyncio
from dataclasses import replace

from sarangbang import (
    GENERIC_KO,
    POLICY_KO,
    DictAdapter,
    FakeLane,
    PersonPrompt,
    Room,
    StaticSections,
    build_room,
    load_scenario,
    load_spec,
    run_rooms,
)
from sarangbang import material as M

TOY = load_scenario("toy_library")


def _build(**kw):
    ad = DictAdapter()
    ps = TOY["personas"]
    given = [[] for _ in ps]
    return build_room(ps, ad.display_names(ps), adapter=ad, digest=TOY["digest"], target=TOY["target"], given=given,
                      cards_by=TOY["cards"], leans=[p.get("lean") for p in ps], **kw)


def test_topic_stance_and_relation_label():
    pol = _build(spec=load_spec("ko_s12"), topic=POLICY_KO)
    gen = _build(spec=load_spec("ko_generic"), topic=GENERIC_KO)
    assert pol[0].before_closing.startswith("당신은 이런 정책에 대체로 찬성해 온 사람이다.")
    assert gen[0].before_closing.startswith("당신은 이 일을 대체로 좋게 보는 사람이다.")
    assert "[이 정책과 나]" in pol[0].system and "[이 일과 나]" in gen[0].system
    assert "정책" not in gen[0].system.replace(TOY["title"], "")


def test_topic_tiers():
    t = replace(GENERIC_KO, strong=0.8)
    assert [t.tier(x) for x in (0.9, 0.7, 0.1, 0.01, None, -0.4)] == ["강찬", "중찬", "약찬", "없음", "없음", "중반"]


def test_material_uses_topic_prompts():
    seen = []

    def llm(system, user, max_tokens=0):
        seen.append((system, user))
        return {"text": "안녕하세요"}, 0.0
    M.seed_message(llm, "제목", TOY["digest"], ["40대"], topic=GENERIC_KO)
    assert seen[0][0] == GENERIC_KO.seed_system and seen[0][1].startswith("[소식] 제목")


class _Plug:
    def system_sections(self, p, i, ctx):
        return [f"[오늘 날씨] 비 — {ctx['topic'].noun}"] if i == 0 else []

    def tail(self, p, i, ctx):
        return "짧게."

    def call_context(self, room, i):
        return f"(지금 메시지 {room.n_say()}개)"


def test_plugin_points():
    out = _build(plugins=[_Plug(), StaticSections(["[공통] 반말로 말한다"])])
    assert "[오늘 날씨] 비 — 소식" in out[0].system and "[오늘 날씨]" not in out[1].system
    assert all("[공통] 반말로 말한다" in o.system for o in out)
    assert out[0].system.index("[공통]") < out[0].system.index("단톡방에서 실제로 할 말만")
    assert all(o.before_closing.endswith("짧게.") for o in out)

    seen = []
    ps = [{"name": "a"}, {"name": "b"}]
    pr = [PersonPrompt(system="s", before_closing="꼬리", closing="끝") for _ in ps]
    r = Room("r", ps, ["a", "b"], pr, {}, {"author": 0, "text": "x"}, target_msgs=3, plugins=[_Plug()])

    def reply(messages):
        seen.append(messages[1]["content"])
        return "응"
    asyncio.run(run_rooms([r], {"base": FakeLane("base", reply)}, poll=0.01))
    assert "(지금 메시지 1개)\n\n꼬리" in seen[0]
