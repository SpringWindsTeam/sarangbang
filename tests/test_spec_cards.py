import json

from sarangbang import DictAdapter, allocate, build_room, hearsay_fill, kept, load_scenario, load_spec

TOY = load_scenario("toy_library")


def _given():
    ad = DictAdapter()
    keep = kept(TOY["relevance"], TOY["cards"])
    return ad, keep, hearsay_fill(allocate(keep, TOY["personas"], 1, TOY["relevance"], ad), keep, TOY["relevance"])


def test_allocate_respects_require():
    _, _, given = _given()
    owner = {x["card"]: i for i, v in enumerate(given) for x in v if not x.get("hearsay_only")}
    assert owner.get("c4") == 2            # 학생 카드는 학생만
    assert all(len(v) <= 1 for v in given)


def test_build_room_sections():
    ad, _, given = _given()
    ps = TOY["personas"]
    out = build_room(ps, ad.display_names(ps), adapter=ad, digest=TOY["digest"], target=TOY["target"], given=given,
                     cards_by=TOY["cards"], leans=[p.get("lean") for p in ps], spec=load_spec())
    assert out[0].system.startswith("너는 '소소한 이야기방' 단톡방에 있는 '마포'이다.")
    assert "[알고 있는 것]" in out[0].system and "[관심사]" in out[0].system
    assert out[0].stance_tier == "중찬" and out[0].light_support
    assert out[1].stance_tier == "중반" and not out[1].light_support
    assert "[학생으로서] 너는 지금 고2이다." in out[2].system
    assert out[3].stance_tier == "없음" and out[3].before_closing.startswith("(너: 30대 자영업)")


def test_load_spec_by_path(tmp_path):
    p = tmp_path / "mine.json"
    p.write_text(json.dumps({"closing": "끝"}), encoding="utf-8")
    assert load_spec(str(p))["_id"] == "mine"
