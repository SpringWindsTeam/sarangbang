"""examples/knowledge-bases의 예시가 점검을 통과하고, 모델 없이 끝까지 돌며, 시나리오로 내보내도 sarangbang run 경로로 도는지."""
from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
sys.path.insert(0, str(EXAMPLES))

from kb_tools.export import to_scenario  # noqa: E402
from kb_tools.kb import load_topic  # noqa: E402
from kb_tools.run import run  # noqa: E402
from kb_tools.validate import check  # noqa: E402

from sarangbang import run_rooms  # noqa: E402
from sarangbang import scenario as S  # noqa: E402

KBS = sorted(p for p in (EXAMPLES / "knowledge-bases").iterdir() if (p / "meta.json").exists())


@pytest.mark.parametrize("root", KBS, ids=lambda p: p.name)
def test_validate_clean(root):
    errors, warns = check(root)
    assert errors == [] and warns == []


@pytest.mark.parametrize("root", KBS, ids=lambda p: p.name)
def test_fake_run(root, tmp_path):
    s = run(root, fake=True, msgs=10, out_dir=tmp_path, quiet=True)
    assert s["messages"] >= 10 and s["stop"] == "target"
    assert s["with_cards"] == s["personas"]             # 예시는 모든 시민이 카드를 받도록 구성
    assert (tmp_path / root.name / "messages.jsonl").exists() and (tmp_path / root.name / "prompts.json").exists()


@pytest.mark.parametrize("root", KBS, ids=lambda p: p.name)
def test_export_runs_as_scenario(root):
    d, _ = to_scenario(root)
    prep = S.prepare(d)
    room = S.make_room(d, prep, S.seed_share(d, prep, None), target_msgs=8)
    stats = asyncio.run(run_rooms([room], {"base": S.fake_lane()}))
    assert stats["rooms"][0]["messages"] >= 8


def test_topic_override():
    t = load_topic({"base": "generic", "noun": "요금 인상", "label": "[서비스 소식]", "common_words": ["요금"]})
    assert t.label == "[서비스 소식]" and "요금" in t.common_words


def test_validate_catches_problems(tmp_path):
    d = tmp_path / "kb"
    shutil.copytree(KBS[0], d)
    cards = json.loads((d / "cards.json").read_text(encoding="utf-8"))
    first = next(iter(cards.values()))
    first["stance_lean"]["lean"] = "모름"
    first["require"] = ["nobody_has_this"]
    (d / "cards.json").write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    errors, warns = check(d)
    assert any("stance_lean" in e for e in errors)
    assert any("nobody_has_this" in w for w in warns)
