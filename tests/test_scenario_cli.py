import json

import pytest

from sarangbang import load_scenario
from sarangbang import scenario as S
from sarangbang.cli import main


def test_builtin_scenario_prepare():
    d = load_scenario("toy_library")
    prep = S.prepare(d)
    assert prep.names == ["마포", "은평", "서대문", "용산"] and prep.sharer == 0
    assert prep.topic.noun == "소식" and prep.spec["_id"] == "ko_generic"
    pol = S.prepare(d, topic="policy")
    assert pol.spec["_id"] == "ko_s12" and pol.topic.noun == "정책"
    with pytest.raises(ValueError):
        S.prepare(d, topic="nope")
    with pytest.raises(FileNotFoundError):
        load_scenario("missing")


def test_room_from_scenario_runs_fake(tmp_path):
    d = load_scenario("toy_library")
    d.update(room_name="테스트방", share="첫 메시지입니다", days=2, day_reset=True)
    prep = S.prepare(d)
    assert prep.scene.room_name == "테스트방"
    room = S.make_room(d, prep, S.seed_share(d, prep, None), target_msgs=5)
    assert room.msgs[0]["text"] == "첫 메시지입니다" and room.days == 2 and room.day_reset
    assert S.format_line(room, room.msgs[0]).startswith("#  1 07:00 마포: 첫 메시지입니다")
    out = S.transcript(d, room)
    assert out["title"] == d["title"] and len(out["messages"]) == 1


def test_cli_quickstart_fake(capsys, tmp_path):
    out = tmp_path / "run.json"
    assert main(["quickstart", "--fake", "--msgs", "6", "--out", str(out)]) == 0
    cap = capsys.readouterr().out
    assert "#  1 07:00 마포:" in cap and '"stop": "target"' in cap
    d = json.loads(out.read_text(encoding="utf-8"))
    assert len(d["messages"]) == 6 and d["stop"] == "target"


def test_cli_run_custom_scenario(capsys, tmp_path):
    sc = {"title": "t", "digest": {"summary": "s", "facts": [{"statement": "f"}]}, "target": {},
          "personas": [{"name": "a", "me": "x", "score": 1}, {"name": "b", "me": "y"}], "share": "공유"}
    p = tmp_path / "s.json"
    p.write_text(json.dumps(sc, ensure_ascii=False), encoding="utf-8")
    assert main(["run", str(p), "--fake", "--msgs", "3"]) == 0
    assert "#  1 07:00 a: 공유" in capsys.readouterr().out


def test_cli_no_model_config(monkeypatch, capsys):
    for k in ("SARANGBANG_BASE_URL", "SARANGBANG_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    assert main(["quickstart"]) == 2
    assert "--fake" in capsys.readouterr().err


def test_cli_lists(capsys):
    assert main(["providers"]) == 0
    out = capsys.readouterr().out
    assert "UPSTAGE_API_KEY" in out and "clovastudio" in out
    assert main(["models", "--vendor", "카카오", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows and all("kakaocorp" in r["id"] for r in rows)
    assert main(["doctor", "--provider", "upstage"]) == 2   # 키 없음
    assert "UPSTAGE_API_KEY" in capsys.readouterr().out
