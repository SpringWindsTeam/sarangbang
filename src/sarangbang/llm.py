"""모델 백엔드 — OpenAI 호환 /chat/completions.

- `Lane`: 단톡방 발화 레인. 동시 호출 수(slots)를 가진 한 모델 엔드포인트. 호출은 동기(엔진이 스레드로 돌린다).
- `JsonLLM`: 재료 준비용 JSON 호출(temperature 0, 응답에서 JSON 객체 하나를 뽑는다).
- `FakeLane`: 시험·예제용 — 정해 둔 함수로 답한다(네트워크 없음).

매 호출은 system + user 두 메시지의 독립 호출이다(모델 쪽 기억 없음).
"""
from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

# 발화 표본 추출 기본값(한국어 단톡방 비교 시험에서 고른 값). enable_thinking은 vLLM 계열 추론 모델의 생각 끄기.
SAMPLING = {"temperature": 0.7, "presence_penalty": 0.4, "frequency_penalty": 0.3,
            "chat_template_kwargs": {"enable_thinking": False}}
_RETRY_STATUS = (429, 500, 502, 503, 504)


@dataclass
class Lane:
    name: str          # 엔진 안 레인 이름(예: "anchor" · "base")
    label: str         # 기록용 모델 이름
    url: str           # .../chat/completions 전체 주소
    key: str
    model: str
    slots: int = 1     # 이 레인의 전체 동시 호출 수(방들이 함께 쓴다)
    verify: str | bool = True
    timeout: float = 180.0
    extra: dict = field(default_factory=dict)   # 요청 본문에 덧붙일 값(SAMPLING을 덮어쓴다)
    sampling: dict = field(default_factory=lambda: dict(SAMPLING))

    @classmethod
    def openai(cls, name: str, base_url: str, key: str, model: str, *, label: str | None = None, **kw) -> Lane:
        """base_url(…/v1)로 만든다."""
        return cls(name, label or model, base_url.rstrip("/") + "/chat/completions", key, model, **kw)

    def call(self, messages: list[dict], max_tokens: int = 400) -> dict:
        """→ {ok, content, latency, retries} 또는 {ok: False, error, latency}. 일시 오류(429·5xx)는 6번까지(4·8·12…초),
        그 밖의 예외는 3번까지 다시 시도한다."""
        body = {"model": self.model, "messages": messages, "max_tokens": max_tokens, **self.sampling, **self.extra}
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        t0 = time.time()
        last = ""
        for k in range(6):
            try:
                with httpx.Client(timeout=self.timeout, verify=self.verify) as c:
                    r = c.post(self.url, json=body, headers=headers)
                if r.status_code in _RETRY_STATUS and k < 5:
                    last = f"{r.status_code} {r.text[:200]}"
                    time.sleep(4 * (k + 1))
                    continue
                if r.status_code >= 400:
                    last = f"{r.status_code} {r.text[:200]}"
                    break
                m = r.json()["choices"][0]["message"]
                return {"ok": True, "latency": round(time.time() - t0, 2), "content": m.get("content") or "", "retries": k}
            except Exception as e:  # noqa: BLE001 — 네트워크·파싱 오류는 몇 번 다시
                last = str(e)[:200]
                if k < 2:
                    time.sleep(3)
                    continue
                break
        return {"ok": False, "error": last, "latency": round(time.time() - t0, 2)}


class FakeLane:
    """시험·예제용 레인 — reply(messages)가 돌려준 텍스트로 답한다(네트워크 없음). 엔진이 쓰는 name·label·slots·call만 있다."""

    def __init__(self, name: str, reply: Callable[[list[dict]], str], slots: int = 1, label: str = "fake"):
        self.name, self.label, self.slots, self.reply = name, label, slots, reply

    def call(self, messages: list[dict], max_tokens: int = 400) -> dict:
        return {"ok": True, "latency": 0.0, "content": self.reply(messages), "retries": 0}


class LLMError(RuntimeError):
    pass


@dataclass
class JsonLLM:
    """재료 준비용 — JSON 객체 하나를 돌려받는 호출. 실패하면 LLMError(조용히 대체하지 않는다)."""
    url: str           # .../chat/completions 전체 주소
    key: str
    model: str
    timeout: float = 180.0
    attempts: int = 6
    extra: dict = field(default_factory=lambda: {"chat_template_kwargs": {"enable_thinking": False}})

    @classmethod
    def openai(cls, base_url: str, key: str, model: str, **kw) -> JsonLLM:
        return cls(base_url.rstrip("/") + "/chat/completions", key, model, **kw)

    def __call__(self, system: str, user: str, max_tokens: int = 3000) -> tuple[dict, float]:
        """(JSON, 걸린 초)."""
        if not self.key:
            raise LLMError("API 키가 없습니다")
        body = {"model": self.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": max_tokens, "temperature": 0, **self.extra}
        last = ""
        for k in range(self.attempts):
            t0 = time.time()
            try:
                with httpx.Client(timeout=self.timeout) as c:
                    r = c.post(self.url, json=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
                r.raise_for_status()
                txt = r.json()["choices"][0]["message"]["content"] or ""
                m = re.search(r"\{.*\}", txt, re.DOTALL)
                if m:
                    return json.loads(m.group(0)), round(time.time() - t0, 1)
                last = "JSON 없음: " + txt[:200]
            except Exception as e:  # noqa: BLE001
                last = str(e)[:200]
            time.sleep(3 * (k + 1))
        raise LLMError("JSON 호출 실패: " + last)


JsonCall = Callable[..., "tuple[dict, float]"]   # (system, user, max_tokens=) → (JSON, 초)
