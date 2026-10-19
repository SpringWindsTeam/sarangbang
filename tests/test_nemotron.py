"""Nemotron-Personas-Korea 증강판 행 6개(CC BY 4.0, 합성 데이터 — tests/data_nemotron_sample.json)로 어댑터를 확인한다."""
import json
from pathlib import Path

from sarangbang import GENERIC_KO, build_room, load_spec
from sarangbang.adapters import NemotronKoreaAdapter

ROWS = json.loads((Path(__file__).parent / "data_nemotron_sample.json").read_text(encoding="utf-8"))
TARGET = {"relations": [{"if": {"has_children": True}, "text": "자녀가 있어 아이들 일에 관심이 많다", "score": 2},
                        {"if": {"province": ["서울", "경기"]}, "text": "수도권에 산다", "score": 1}]}


def test_lines():
    ad = NemotronKoreaAdapter()
    p = ROWS[0]
    me = ad.me_line(p)
    assert me.startswith(f"{p['age']}세 {p['sex']}") and "인천 연수구에 산다" in me
    assert ad.display_names(ROWS)[0] == "연수"
    assert len(set(ad.display_names(ROWS))) == len(ROWS)
    kid = next(r for r in ROWS if r["has_children"])
    assert "[우리 아이] 자녀가 있다" in ad.fact_sections(kid, TARGET)
    assert ad.affected(kid, TARGET) and ad.static_score(kid, TARGET) >= 2
    assert "parent" in ad.tags(kid) and "학부모" in ad.own_perspectives(kid)


def test_story_optional():
    p = ROWS[0]
    assert not any(s.startswith("[내 이야기]") for s in NemotronKoreaAdapter().fact_sections(p, TARGET))
    assert any(s.startswith("[내 이야기]") for s in NemotronKoreaAdapter(include_story=True).fact_sections(p, TARGET))


def test_build_room_with_rows():
    ad = NemotronKoreaAdapter()
    digest = {"summary": "동네 공영주차장 요금이 오른다.", "facts": [{"statement": "다음 달부터 공영주차장 요금이 시간당 500원 오른다"}]}
    out = build_room(ROWS, ad.display_names(ROWS), adapter=ad, digest=digest, target=TARGET, given=[[] for _ in ROWS],
                     cards_by={}, leans=[0.4, -0.4, None, 0.1, -0.1, None], spec=load_spec("ko_generic"), topic=GENERIC_KO)
    assert len(out) == 6 and all("[알고 있는 것]" in o.system for o in out)
    kid_i = next(i for i, r in enumerate(ROWS) if r["has_children"])
    assert "[이 일과 나] 자녀가 있어 아이들 일에 관심이 많다" in out[kid_i].system
