"""`sarangbang` 명령 — 설치 뒤 바로 돌려 보고, 국산 모델 제공처를 고르고, 연결을 점검한다.

    sarangbang quickstart --fake               # 네트워크 없이 내장 시나리오로 흐름 확인
    sarangbang providers                       # 국산 AI를 쓸 수 있는 곳(프리셋)과 환경 변수
    sarangbang models                          # 오픈 웨이트 국산 모델 목록과 vllm serve 힌트
    sarangbang doctor --provider upstage       # 키·주소·모델 연결 점검(짧은 호출 한 번)
    sarangbang run scenario.json --provider vllm --model skt/A.X-4.0-Light --msgs 40 --out run.json

모델은 --provider/--model(+ 제공처 키 환경 변수) 또는 SARANGBANG_PROVIDER / SARANGBANG_BASE_URL·SARANGBANG_API_KEY·SARANGBANG_MODEL로 고른다.
앵커 레인(정적 점수 상위 시민용 큰 모델)은 --anchor-provider/--anchor-model 또는 SARANGBANG_ANCHOR_* 로 따로 준다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from . import __version__
from . import providers as P
from . import scenario as S
from .engine import run_rooms
from .llm import JsonLLM, Lane


def _lane(a: argparse.Namespace, name: str, *, anchor: bool = False) -> Lane | None:
    """인자 → 환경 변수 순으로 레인을 만든다. 앵커는 설정이 없으면 None."""
    pid = a.anchor_provider if anchor else a.provider
    model = a.anchor_model if anchor else a.model
    base = getattr(a, "base_url", None) if not anchor else None
    key = os.environ.get(a.api_key_env, "") if getattr(a, "api_key_env", None) else ""
    slots = a.anchor_slots if anchor else a.slots
    extra = json.loads(a.extra) if getattr(a, "extra", None) else {}
    if base:
        p = P._guess(base)
        if not model:
            raise SystemExit("--base-url에는 --model이 필요합니다")
        return Lane.openai(name, base, key or ("EMPTY" if p and p.key_optional else key), model, slots=slots,
                           sampling=dict(p.sampling if p else P._OPENAI), extra=extra)
    if pid:
        return P.get_provider(pid).lane(name, model=model or None, key=key or None, slots=slots, extra=extra)
    prefix = "SARANGBANG_ANCHOR" if anchor else "SARANGBANG"
    if P.configured(prefix):
        return P.lane_from_env(name, prefix=prefix, slots=slots, extra=extra)
    return None


def _json_llm(a: argparse.Namespace, lane: Lane) -> JsonLLM:
    """재료 준비용 호출 — 발화 레인과 같은 서버·모델."""
    p = P._guess(lane.url)
    return JsonLLM.openai(lane.url.removesuffix("/chat/completions"), lane.key, lane.model, extra=dict(p.json_extra) if p else {})


def cmd_run(a: argparse.Namespace) -> int:
    d = S.load_scenario(a.scenario)
    prep = S.prepare(d, topic=a.topic, spec=a.spec)
    lanes: dict = {}
    if a.fake:
        lanes["base"] = S.fake_lane(slots=a.slots)
        share = S.seed_share(d, prep, None)
    else:
        base = _lane(a, "base")
        if base is None:
            print("모델 설정이 없습니다. 네트워크 없이 보려면 --fake, 모델을 쓰려면 --provider <이름> 또는 SARANGBANG_* 환경 변수를 주세요.\n"
                  "  sarangbang providers   # 쓸 수 있는 곳 보기", file=sys.stderr)
            return 2
        lanes["base"] = base
        anchor = _lane(a, "anchor", anchor=True)
        if anchor is not None:
            lanes["anchor"] = anchor
        share = S.seed_share(d, prep, _json_llm(a, lanes.get("anchor") or base))
    room = S.make_room(d, prep, share, target_msgs=a.msgs)
    print(S.format_line(room, room.msgs[0]))
    stats = asyncio.run(run_rooms([room], lanes, on_message=lambda r, m: print(S.format_line(r, m), flush=True)))
    print(json.dumps(stats, ensure_ascii=False))
    if a.out:
        Path(a.out).write_text(json.dumps(S.transcript(d, room, stats), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"저장: {a.out}")
    return 0


def cmd_providers(a: argparse.Namespace) -> int:
    rows = list(P.PROVIDERS.values())
    if a.json:
        print(json.dumps([p.__dict__ for p in rows], ensure_ascii=False, indent=1))
        return 0
    print("국산 AI를 쓸 수 있는 곳 — --provider <id> 또는 SARANGBANG_PROVIDER=<id> (키는 환경 변수)\n")
    for kind in (P.HOSTED, P.GATEWAY, P.LOCAL):
        print(f"[{P.KIND_KO[kind]}]")
        for p in rows:
            if p.kind != kind:
                continue
            mark = "✓" if os.environ.get(p.key_env) else ("·" if p.key_optional else " ")
            models = ", ".join(p.models) if p.models else "(모델 이름을 --model로)"
            print(f" {mark} {p.id:<10} {p.name}\n    주소  {p.base_url}\n    키    {p.key_env}{'  (없어도 됨)' if p.key_optional else ''}\n    모델  {models}")
            if p.notes:
                print(f"    참고  {p.notes}")
        print()
    print("✓ = 키 환경 변수가 설정됨. 자세한 안내: docs/korean-ai-providers.md")
    return 0


def cmd_models(a: argparse.Namespace) -> int:
    rows = P.models_by_vendor(a.vendor)
    if a.json:
        print(json.dumps([m.__dict__ for m in rows], ensure_ascii=False, indent=1))
        return 0
    print("오픈 웨이트 국산 모델(2026-10 기준) — 라이선스 요약은 참고용이며 사용 전 전문을 읽으세요.\n")
    for m in rows:
        off = f" · 추론 끄기: {m.thinking_off}" if m.thinking_off else ""
        print(f"- {m.id}\n    {m.vendor} · {m.params} · {m.license} · 상업 이용 {m.commercial}{off}")
        if m.serve:
            print(f"    vllm serve {m.id} {m.serve}")
        if m.note:
            print(f"    {m.note}")
    print("\n띄운 뒤: sarangbang doctor --provider vllm --model <id>")
    return 0


def cmd_doctor(a: argparse.Namespace) -> int:
    import httpx

    try:
        lane = _lane(a, "base")
    except (KeyError, ValueError) as e:
        print(f"✗ {e}")
        return 2
    if lane is None:
        print("✗ 모델 설정이 없습니다 — --provider <id> (+ 키 환경 변수) 또는 SARANGBANG_* 환경 변수를 주세요.")
        return 2
    base = lane.url.removesuffix("/chat/completions")
    print(f"주소   {base}\n모델   {lane.model}\n키     {'있음' if lane.key and lane.key != 'EMPTY' else '없음(로컬 서버 가정)'}")
    headers = {"Authorization": f"Bearer {lane.key}"}
    try:
        r = httpx.get(base + "/models", headers=headers, timeout=20)
        if r.status_code == 200:
            ids = [m.get("id") for m in (r.json().get("data") or [])][:50]
            hit = lane.model in ids
            print(f"✓ /models {len(ids)}개 — {'모델 있음' if hit else '목록에 모델 이름이 없음(별칭일 수 있음)'}")
            if not hit and ids:
                near = [i for i in ids if any(k in (i or '').lower() for k in ('exaone', 'a.x', 'solar', 'hcx', 'kanana', 'midm', 'k-'))]
                if near:
                    print("  국산 모델로 보이는 것: " + ", ".join(near[:10]))
        else:
            print(f"· /models {r.status_code} (지원하지 않는 서버도 있음)")
    except Exception as e:  # noqa: BLE001
        print(f"· /models 실패: {str(e)[:120]}")
    t0 = time.time()
    res = lane.call([{"role": "system", "content": "짧게 답한다."}, {"role": "user", "content": "안녕하세요. 한 단어로 인사해 주세요."}], max_tokens=16)
    if res.get("ok"):
        print(f"✓ chat/completions {res['latency']}초 — 응답: {res['content'].strip()[:60]!r}")
        if not res["content"].strip():
            print("  ! 내용이 비었습니다 — 추론 모드가 켜져 있을 수 있습니다(모델 목록의 '추론 끄기' 참고).")
        return 0
    print(f"✗ chat/completions 실패({round(time.time() - t0, 1)}초): {res.get('error')}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sarangbang", description="한국어 단톡방 여론 시뮬레이션 엔진")
    ap.add_argument("--version", action="version", version=f"sarangbang {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def model_args(p: argparse.ArgumentParser, *, anchor: bool = True) -> None:
        g = p.add_argument_group("모델")
        g.add_argument("--provider", help=f"제공처 프리셋: {', '.join(P.PROVIDERS)}")
        g.add_argument("--model", help="모델 이름(프리셋 기본값을 덮어씀)")
        g.add_argument("--base-url", help="아무 OpenAI 호환 서버의 …/v1 주소(--provider 대신)")
        g.add_argument("--api-key-env", help="키를 읽을 환경 변수 이름(기본: 프리셋의 환경 변수)")
        g.add_argument("--slots", type=int, default=2, help="기본 레인 동시 호출 수(기본 2)")
        g.add_argument("--extra", help='요청 본문에 덧붙일 JSON(예: \'{"reasoning_effort":"none"}\')')
        if anchor:
            g.add_argument("--anchor-provider", help="앵커 레인(정적 점수 상위 시민) 제공처")
            g.add_argument("--anchor-model", help="앵커 레인 모델")
            g.add_argument("--anchor-slots", type=int, default=1)

    r = sub.add_parser("run", help="시나리오 JSON으로 방 하나를 돌린다")
    r.add_argument("scenario", help="시나리오 JSON 경로 또는 내장 이름(toy_library)")
    r.add_argument("--msgs", type=int, default=30, help="목표 메시지 수(기본 30)")
    r.add_argument("--topic", choices=sorted(S.TOPICS), help="주제 문구 세트(시나리오의 topic을 덮어씀)")
    r.add_argument("--spec", help="사양 이름 또는 JSON 경로")
    r.add_argument("--fake", action="store_true", help="네트워크 없이 정해 둔 문장으로")
    r.add_argument("--out", help="결과(메시지·호출 기록) JSON 저장 경로")
    model_args(r)
    r.set_defaults(fn=cmd_run)

    q = sub.add_parser("quickstart", help="내장 시나리오(도서관 야간 개관 · 시민 4명)를 돌린다")
    q.add_argument("--msgs", type=int, default=12)
    q.add_argument("--topic", choices=sorted(S.TOPICS), default=None)
    q.add_argument("--fake", action="store_true", help="네트워크 없이")
    q.add_argument("--out")
    model_args(q)
    q.set_defaults(fn=cmd_run, scenario="toy_library", spec=None)

    pv = sub.add_parser("providers", help="국산 AI를 쓸 수 있는 곳(프리셋)")
    pv.add_argument("--json", action="store_true")
    pv.set_defaults(fn=cmd_providers)

    md = sub.add_parser("models", help="오픈 웨이트 국산 모델 목록")
    md.add_argument("--vendor", help="예: LG, SK, 업스테이지, 네이버, 카카오, KT")
    md.add_argument("--json", action="store_true")
    md.set_defaults(fn=cmd_models)

    dc = sub.add_parser("doctor", help="모델 연결 점검(짧은 호출 한 번)")
    model_args(dc, anchor=False)
    dc.set_defaults(fn=cmd_doctor)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return int(a.fn(a) or 0)
    except (KeyError, ValueError, FileNotFoundError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
