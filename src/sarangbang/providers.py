"""모델 제공처(provider) 프리셋 — 국산 AI를 쓸 수 있는 곳과 오픈 웨이트 모델 목록.

sarangbang은 OpenAI 호환 `/chat/completions`만 쓴다. 여기서는 한국어 모델을 쓸 수 있는 대표 경로를 프리셋으로 묶어
`Lane`·`JsonLLM`을 한 줄로 만들 수 있게 한다. 세 갈래다.

- hosted : 국내 기업이 직접 운영하는 API — 업스테이지 Solar, 네이버클라우드 CLOVA Studio(HyperCLOVA X)
- gateway: 여러 모델을 중개하는 플랫폼 — FriendliAI, OpenRouter. 국산 모델이 올라와 있을 때 쓴다(목록은 바뀐다)
- local  : 오픈 웨이트를 직접 띄운 서버 — vLLM, SGLang, Ollama, LM Studio. EXAONE·A.X·K-EXAONE·Solar Open·HyperCLOVA X SEED·
           Kanana·Mi:dm 등 `OPEN_MODELS`의 모델을 받아 띄운다

프리셋은 주소·키 환경 변수·추천 모델·표본 추출 기본값(그 서버가 받는 인자만)을 담는다. 모델 이름·가격·제공 여부는 자주 바뀌므로
`sarangbang doctor`로 실제 연결을 확인하고, 자세한 안내는 docs/korean-ai-providers.md를 본다.

    from sarangbang import get_provider
    lane = get_provider("upstage").lane("base", slots=4)          # UPSTAGE_API_KEY 환경 변수 사용
    llm = get_provider("vllm").json_llm(model="skt/A.X-4.0-Light")  # http://localhost:8000/v1

환경 변수만으로 고르려면 `lane_from_env()` — SARANGBANG_PROVIDER=upstage 또는 SARANGBANG_BASE_URL·SARANGBANG_API_KEY·SARANGBANG_MODEL.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .llm import SAMPLING, JsonLLM, Lane

HOSTED, GATEWAY, LOCAL = "hosted", "gateway", "local"
KIND_KO = {HOSTED: "국내 기업 API", GATEWAY: "중개 플랫폼", LOCAL: "직접 띄운 서버"}

# 표본 추출 기본값 — 서버가 받는 인자만 보낸다. OpenAI 호환이라도 모르는 인자를 거부하는 서버가 있다.
_VLLM = dict(SAMPLING)                                                              # vLLM·SGLang: chat_template_kwargs로 생각 끄기
_OPENAI = {"temperature": 0.7, "presence_penalty": 0.4, "frequency_penalty": 0.3}   # 일반 호스팅 API
_CLOVA = {"temperature": 0.7}                                                       # CLOVA Studio: presence/frequency_penalty 미지원
_THINK_OFF = {"chat_template_kwargs": {"enable_thinking": False}}


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    kind: str                       # hosted | gateway | local
    base_url: str                   # …/v1
    key_env: str                    # API 키 환경 변수 이름
    models: tuple[str, ...] = ()    # 추천 모델 — 첫 번째가 기본값. local은 모델 이름을 직접 준다
    sampling: dict = field(default_factory=lambda: dict(_OPENAI))
    json_extra: dict = field(default_factory=dict)   # JsonLLM 요청에 덧붙일 값
    key_optional: bool = False      # 로컬 서버는 키가 없어도 된다("EMPTY")
    docs: str = ""
    notes: str = ""

    @property
    def default_model(self) -> str:
        return self.models[0] if self.models else ""

    def key(self, key: str | None = None) -> str:
        """명시한 키 → 환경 변수 → (로컬이면) "EMPTY". 없으면 KeyError."""
        k = key or os.environ.get(self.key_env, "")
        if not k and self.key_optional:
            return "EMPTY"
        if not k:
            raise KeyError(f"{self.name} API 키가 없습니다 — 환경 변수 {self.key_env}를 설정하세요")
        return k

    def lane(self, name: str = "base", *, model: str | None = None, key: str | None = None, base_url: str | None = None,
             slots: int = 1, label: str | None = None, sampling: dict | None = None, **kw) -> Lane:
        """이 제공처로 발화 레인을 만든다. model이 없으면 추천 모델의 첫 번째."""
        m = model or self.default_model
        if not m:
            raise ValueError(f"{self.name}: 모델 이름을 주세요(예: model=\"{self._model_hint()}\")")
        return Lane.openai(name, base_url or self.base_url, self.key(key), m, label=label or m, slots=slots,
                           sampling=dict(sampling if sampling is not None else self.sampling), **kw)

    def json_llm(self, *, model: str | None = None, key: str | None = None, base_url: str | None = None, **kw) -> JsonLLM:
        """재료 준비용 JSON 호출 객체."""
        m = model or self.default_model
        if not m:
            raise ValueError(f"{self.name}: 모델 이름을 주세요(예: model=\"{self._model_hint()}\")")
        kw.setdefault("extra", dict(self.json_extra))
        return JsonLLM.openai(base_url or self.base_url, self.key(key), m, **kw)

    def _model_hint(self) -> str:
        return self.models[0] if self.models else OPEN_MODELS[0].id


PROVIDERS: dict[str, Provider] = {p.id: p for p in (
    Provider("upstage", "Upstage Solar", HOSTED, "https://api.upstage.ai/v1", "UPSTAGE_API_KEY",
             ("solar-pro4", "solar-mini4", "solar-pro3", "solar-pro2"),
             docs="https://console.upstage.ai/docs",
             notes="OpenAI SDK 호환. 추론 모드가 있는 모델은 요청에 reasoning_effort를 줄 수 있다(Lane(extra=…))."),
    Provider("clova", "NAVER CLOVA Studio (HyperCLOVA X)", HOSTED, "https://clovastudio.stream.ntruss.com/v1/openai",
             "CLOVASTUDIO_API_KEY", ("HCX-005", "HCX-DASH-002", "HCX-007"), sampling=dict(_CLOVA),
             docs="https://api.ncloud-docs.com/docs/clovastudio-openaicompatibility",
             notes="presence_penalty·frequency_penalty 미지원(제외함). repetition_penalty는 CLOVA 전용 인자. HCX-007은 추론 모델."),
    Provider("friendli", "FriendliAI (Model APIs)", GATEWAY, "https://api.friendli.ai/serverless/v1", "FRIENDLI_TOKEN", (),
             docs="https://friendli.ai/docs/guides/openai-compatibility",
             notes="EXAONE·K-EXAONE을 서빙해 온 플랫폼. 현재 목록은 GET /models 또는 friendli.ai/models에서 확인(Dedicated Endpoints는 임의 모델)."),
    Provider("openrouter", "OpenRouter", GATEWAY, "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
             ("upstage/solar-pro4", "upstage/solar-mini4", "upstage/solar-pro-3"),
             docs="https://openrouter.ai/models?q=upstage",
             notes="국산 모델 중 Upstage Solar 계열이 올라와 있다(2026-10). 목록은 바뀐다."),
    Provider("vllm", "vLLM (self-hosted)", LOCAL, "http://localhost:8000/v1", "VLLM_API_KEY", (), sampling=dict(_VLLM),
             json_extra=dict(_THINK_OFF), key_optional=True, docs="https://docs.vllm.ai",
             notes="`vllm serve <HF 모델>`로 띄운 서버. chat_template_kwargs.enable_thinking=false로 추론 모드를 끈다(EXAONE·A.X·K-EXAONE)."),
    Provider("sglang", "SGLang (self-hosted)", LOCAL, "http://localhost:30000/v1", "SGLANG_API_KEY", (), sampling=dict(_VLLM),
             json_extra=dict(_THINK_OFF), key_optional=True, docs="https://docs.sglang.ai",
             notes="`python -m sglang.launch_server --model-path <HF 모델>`."),
    Provider("ollama", "Ollama (local)", LOCAL, "http://localhost:11434/v1", "OLLAMA_API_KEY",
             ("exaone3.5:7.8b", "exaone3.5:2.4b", "exaone-deep:7.8b"), key_optional=True, docs="https://ollama.com/library/exaone3.5",
             notes="노트북에서 EXAONE 3.5를 바로 돌릴 수 있다(`ollama pull exaone3.5:7.8b`). GGUF 변환본(A.X·Kanana·Mi:dm)도 Modelfile로 등록 가능."),
    Provider("lmstudio", "LM Studio (local)", LOCAL, "http://localhost:1234/v1", "LMSTUDIO_API_KEY", (), key_optional=True,
             docs="https://lmstudio.ai/docs/app/api/endpoints/openai",
             notes="앱에서 받은 모델 이름을 그대로 model에 준다."),
)}


def get_provider(id_: str) -> Provider:
    """프리셋 이름(upstage · clova · friendli · openrouter · vllm · sglang · ollama · lmstudio)."""
    try:
        return PROVIDERS[id_.lower()]
    except KeyError:
        raise KeyError(f"모르는 제공처 '{id_}' — 가능한 값: {', '.join(PROVIDERS)}") from None


# ── 환경 변수로 고르기 ──
def _env(prefix: str, k: str) -> str:
    return os.environ.get(f"{prefix}_{k}", "")


def lane_from_env(name: str = "base", *, prefix: str = "SARANGBANG", slots: int | None = None, **kw) -> Lane:
    """환경 변수로 레인 하나를 만든다. 둘 중 하나다.

    1. {prefix}_BASE_URL · {prefix}_API_KEY · {prefix}_MODEL — 아무 OpenAI 호환 서버
    2. {prefix}_PROVIDER=upstage|clova|… (+ {prefix}_MODEL 선택, 키는 제공처의 환경 변수 또는 {prefix}_API_KEY)
    {prefix}_SLOTS로 동시 호출 수를 준다(기본 2). 앵커 레인은 prefix="SARANGBANG_ANCHOR"처럼 접두사를 바꿔 따로 만든다."""
    n = slots if slots is not None else int(_env(prefix, "SLOTS") or 2)
    base, key, model, pid = (_env(prefix, k) for k in ("BASE_URL", "API_KEY", "MODEL", "PROVIDER"))
    if base:
        if not model:
            raise KeyError(f"{prefix}_MODEL이 없습니다")
        p = _guess(base)
        return Lane.openai(name, base, key or ("EMPTY" if p and p.key_optional else key), model, slots=n,
                           sampling=dict(p.sampling if p else _OPENAI), **kw)
    if pid:
        return get_provider(pid).lane(name, model=model or None, key=key or None, slots=n, **kw)
    raise KeyError(f"모델 설정이 없습니다 — {prefix}_PROVIDER(예: upstage, vllm) 또는 {prefix}_BASE_URL·{prefix}_API_KEY·{prefix}_MODEL을 설정하세요. "
                   "네트워크 없이 보려면 --fake.")


def json_llm_from_env(*, prefix: str = "SARANGBANG", **kw) -> JsonLLM:
    """lane_from_env와 같은 환경 변수로 재료 준비용 JsonLLM을 만든다."""
    base, key, model, pid = (_env(prefix, k) for k in ("BASE_URL", "API_KEY", "MODEL", "PROVIDER"))
    if base:
        if not model:
            raise KeyError(f"{prefix}_MODEL이 없습니다")
        p = _guess(base)
        kw.setdefault("extra", dict(p.json_extra) if p else {})
        return JsonLLM.openai(base, key or ("EMPTY" if p and p.key_optional else key), model, **kw)
    if pid:
        return get_provider(pid).json_llm(model=model or None, key=key or None, **kw)
    raise KeyError(f"모델 설정이 없습니다 — {prefix}_PROVIDER 또는 {prefix}_BASE_URL·{prefix}_API_KEY·{prefix}_MODEL을 설정하세요.")


def configured(prefix: str = "SARANGBANG") -> bool:
    """환경 변수에 모델 설정이 있는가(lane_from_env가 성공할 조건)."""
    return bool(_env(prefix, "BASE_URL") or _env(prefix, "PROVIDER"))


def _guess(base_url: str) -> Provider | None:
    """주소로 제공처를 짐작한다(표본 추출 기본값을 고르기 위해). 모르면 None."""
    b = base_url.rstrip("/")
    for p in PROVIDERS.values():
        if b.startswith(p.base_url.rstrip("/")):
            return p
    if "localhost" in b or "127.0.0.1" in b:
        return PROVIDERS["vllm"]
    return None


# ── 오픈 웨이트 국산 모델 목록 ──
@dataclass(frozen=True)
class OpenModel:
    id: str             # Hugging Face 모델 id
    vendor: str
    params: str
    license: str
    commercial: str     # 가능 | 비상업 | 조건부 — 요약일 뿐, 실제 사용 전 라이선스 전문을 읽는다
    thinking_off: str   # 추론 모드 끄는 법(빈 문자열이면 추론 모드 없음)
    serve: str = ""     # `vllm serve <id>` 뒤에 붙일 인자 힌트
    note: str = ""


_ET = "chat_template_kwargs.enable_thinking=false"
OPEN_MODELS: tuple[OpenModel, ...] = (
    OpenModel("LGAI-EXAONE/EXAONE-4.5-33B", "LG AI연구원", "33B", "EXAONE AI Model License 1.2-NC", "비상업", _ET,
              "--reasoning-parser qwen3 --max-model-len 65536", "2026-04. 비전 포함. 연구·교육용 라이선스"),
    OpenModel("LGAI-EXAONE/K-EXAONE-236B-A23B", "LG AI연구원", "236B-A23B MoE", "K-EXAONE License", "조건부", _ET,
              "--tensor-parallel-size 8   (vllm>=0.14)", "독자 AI 파운데이션 모델 1차(2025-12)"),
    OpenModel("LGAI-EXAONE/K-EXAONE-2.0-750B-A37B", "LG AI연구원", "750B-A37B MoE", "Apache-2.0", "가능", _ET + " (모델 카드 확인)",
              "", "독자 AI 파운데이션 모델 2차(2026-08). FP8·NVFP4 판 있음"),
    OpenModel("LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct", "LG AI연구원", "7.8B", "EXAONE AI Model License", "비상업", "",
              "", "노트북용. Ollama `exaone3.5:7.8b`. 2.4B·32B도 있음"),
    OpenModel("skt/A.X-K2", "SK텔레콤", "688B MoE", "Apache-2.0", "가능", _ET,
              "--reasoning-parser deepseek_v3 --tensor-parallel-size 8", "독자 AI 파운데이션 모델 2차(2026-07). NVFP4·GGUF 판 있음"),
    OpenModel("skt/A.X-K1", "SK텔레콤", "519B-A33B MoE", "Apache-2.0", "가능", "Think/Non-Think 모드(모델 카드)",
              "", "독자 AI 파운데이션 모델 1차(2026-01)"),
    OpenModel("skt/A.X-4.0", "SK텔레콤", "72B", "Qwen License", "조건부", "",
              "--tensor-parallel-size 4", "sarangbang 기본 프롬프트를 맞춘 모델 중 하나(A.X). Qwen2.5-72B 기반"),
    OpenModel("skt/A.X-4.0-Light", "SK텔레콤", "7B", "Apache-2.0", "가능", "",
              "", "GPU 한 장. 빠른 레인(base)용으로 알맞다"),
    OpenModel("upstage/Solar-Open2-250B", "업스테이지", "250B-A15B MoE", "Upstage Solar License", "조건부", "reasoning_effort=none",
              "--reasoning-parser solar_open2 --enable-expert-parallel --tensor-parallel-size 8", "독자 AI 파운데이션 모델 2차(2026-07). 'Built with Solar' 표기"),
    OpenModel("upstage/Solar-Open-100B", "업스테이지", "102B-A12B MoE", "Upstage Solar License", "조건부", "reasoning_effort=none",
              "--reasoning-parser solar_open --tensor-parallel-size 8", "독자 AI 파운데이션 모델 1차(2026-01)"),
    OpenModel("naver-hyperclovax/HyperCLOVAX-SEED-Think-32B", "네이버클라우드", "33B", "HyperCLOVA X SEED License", "조건부",
              "chat_template_kwargs.force_reasoning=false", "", "추론 필드 분리는 hcx-vllm-plugin. 14B 판도 있음"),
    OpenModel("naver-hyperclovax/HyperCLOVAX-SEED-Think-14B", "네이버클라우드", "14B", "HyperCLOVA X SEED License", "조건부",
              "chat_template_kwargs.force_reasoning=false", "", "GPU 한 장(bf16 ~30GB)"),
    OpenModel("kakaocorp/kanana-2-30b-a3b-instruct", "카카오", "30B-A3B MoE", "Kanana License", "조건부", "",
              "--enable-auto-tool-choice --tool-call-parser hermes", "API·클라우드 제공·재판매, MAU 1천만 이상은 별도 계약. 'Powered by Kanana' 표기. -thinking 판 별도"),
    OpenModel("kakaocorp/kanana-2-3b-instruct", "카카오", "3.5B", "Kanana Open License", "조건부", "",
              "", "작은 GPU·CPU. 1.3B 판도 있음"),
    OpenModel("K-intelligence/Midm-2.0-Base-Instruct", "KT", "11.5B", "MIT", "가능", "",
              "", "믿:음 2.0. Mini(2.3B) 판도 있음"),
    OpenModel("trillionlabs/Tri-21B-Think", "트릴리온랩스", "21B", "Apache-2.0", "가능", "Tri-21B(비추론 판)를 쓴다",
              "", "Tri-21B 비추론 판은 접근 신청(gated)"),
    OpenModel("Motif-Technologies/Motif-3", "모티프테크놀로지스", "315B MoE", "MIT", "가능", "",
              "--reasoning-parser motif", "독자 AI 파운데이션 모델 2차 참가(패자부활)"),
    OpenModel("NCSOFT/Llama-VARCO-8B-Instruct", "NC AI", "8B", "Llama 3.1 Community", "조건부", "",
              "", "2024-12. Llama 3.1 기반 한국어 특화"),
)


def models_by_vendor(vendor: str | None = None) -> list[OpenModel]:
    return [m for m in OPEN_MODELS if not vendor or vendor in m.vendor or vendor.lower() in m.id.lower()]
