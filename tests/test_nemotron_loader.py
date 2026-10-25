import httpx

from sarangbang.adapters import NEMOTRON_DATASET, load_nemotron_rows
from sarangbang.adapters import nemotron_ko as N


def test_load_rows_pages_and_filters(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        off = int(request.url.params["offset"])
        calls.append(off)
        if off >= 200:
            return httpx.Response(200, json={"rows": []})
        rows = [{"row": {"id": off + k, "province": "서울" if k % 2 else "부산", "has_children": k % 3 == 0}} for k in range(100)]
        return httpx.Response(200, json={"rows": rows})

    real = httpx.Client
    monkeypatch.setattr(N.httpx if hasattr(N, "httpx") else httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    rows = load_nemotron_rows(5, skip=100, province="서울")
    assert len(rows) == 5 and all(r["province"] == "서울" for r in rows) and rows[0]["id"] == 101 and calls[0] == 100
    rows = load_nemotron_rows(500, where={"has_children": True})
    assert rows and all(r["has_children"] for r in rows) and calls[-1] == 200   # 끝까지 읽고 멈춘다
    assert "springwindteam" in NEMOTRON_DATASET
