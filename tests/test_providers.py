import pytest

from sarangbang import OPEN_MODELS, PROVIDERS, get_provider, json_llm_from_env, lane_from_env
from sarangbang import providers as P


def test_catalog_sane():
    assert {"upstage", "clova", "vllm", "ollama"} <= set(PROVIDERS)
    for p in PROVIDERS.values():
        assert p.base_url.startswith("http") and not p.base_url.endswith("/") and p.key_env.isupper()
        assert p.kind in (P.HOSTED, P.GATEWAY, P.LOCAL)
    ids = [m.id for m in OPEN_MODELS]
    assert len(ids) == len(set(ids)) and all("/" in i for i in ids)
    assert all(m.commercial in ("가능", "비상업", "조건부") for m in OPEN_MODELS)
    assert any("A.X" in i for i in ids) and any("EXAONE" in i for i in ids)


def test_lane_uses_provider_sampling(monkeypatch):
    monkeypatch.setenv("CLOVASTUDIO_API_KEY", "k")
    lane = get_provider("clova").lane("base", slots=3)
    assert lane.url == "https://clovastudio.stream.ntruss.com/v1/openai/chat/completions"
    assert "presence_penalty" not in lane.sampling and lane.model == "HCX-005" and lane.slots == 3
    v = get_provider("vllm").lane(model="skt/A.X-4.0-Light")     # 키 없어도 된다
    assert v.key == "EMPTY" and v.sampling["chat_template_kwargs"] == {"enable_thinking": False}
    assert get_provider("vllm").json_llm(model="m").extra == {"chat_template_kwargs": {"enable_thinking": False}}
    assert get_provider("upstage").json_llm(model="solar-pro4", key="k").extra == {}


def test_missing_key_and_model(monkeypatch):
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)
    with pytest.raises(KeyError, match="UPSTAGE_API_KEY"):
        get_provider("upstage").lane()
    with pytest.raises(ValueError, match="모델 이름"):
        get_provider("vllm").lane()
    with pytest.raises(KeyError, match="모르는 제공처"):
        get_provider("nope")


def test_from_env(monkeypatch):
    for k in ("SARANGBANG_BASE_URL", "SARANGBANG_API_KEY", "SARANGBANG_MODEL", "SARANGBANG_PROVIDER", "SARANGBANG_SLOTS"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(KeyError, match="SARANGBANG_PROVIDER"):
        lane_from_env()
    monkeypatch.setenv("SARANGBANG_PROVIDER", "upstage")
    monkeypatch.setenv("SARANGBANG_API_KEY", "k2")
    monkeypatch.setenv("SARANGBANG_MODEL", "solar-mini4")
    monkeypatch.setenv("SARANGBANG_SLOTS", "5")
    lane = lane_from_env()
    assert (lane.key, lane.model, lane.slots) == ("k2", "solar-mini4", 5)
    assert json_llm_from_env().model == "solar-mini4"
    monkeypatch.setenv("SARANGBANG_ANCHOR_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("SARANGBANG_ANCHOR_MODEL", "LGAI-EXAONE/EXAONE-4.5-33B")
    a = lane_from_env("anchor", prefix="SARANGBANG_ANCHOR", slots=1)
    assert a.key == "EMPTY" and "chat_template_kwargs" in a.sampling and a.name == "anchor"
    assert P.configured() and P.configured("SARANGBANG_ANCHOR") and not P.configured("NOPE")
