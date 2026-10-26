"""지식 베이스 폴더 읽기 — meta.json · digest.json · cards.json · personas.json · (relevance.json)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from sarangbang import GENERIC_KO, POLICY_KO, JsonLLM, Topic, json_llm_from_env, load_spec

BASES = {"generic": GENERIC_KO, "policy": POLICY_KO}
LEANS = ("찬성", "반대", "조건부", "중립")
STATUSES = ("확정·시행", "계획·목표", "과거 실적", "검토")   # 기본 상태 어휘. 도메인마다 meta.json "statuses"로 바꾼다
RELS = ("direct", "related", "unrelated")


@dataclass
class KB:
    root: Path
    meta: dict
    digest: dict
    cards: dict[str, dict]
    personas: list[dict]
    relevance: dict[str, str] | None = None
    topic: Topic = field(default=GENERIC_KO)
    spec: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def title(self) -> str:
        return self.meta["title"]

    @property
    def target(self) -> dict:
        return self.meta.get("target") or {}

    @property
    def statuses(self) -> tuple[str, ...]:
        return tuple(self.meta.get("statuses") or STATUSES)


def _read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def load_topic(cfg: dict | None) -> Topic:
    """meta.json의 topic 항목 → sarangbang Topic(base를 복사해 필요한 칸만 바꿈)."""
    cfg = cfg or {}
    base = BASES[cfg.get("base", "generic")]
    kw = {k: cfg[k] for k in ("noun", "label", "relation_label") if cfg.get(k)}
    if cfg.get("common_words"):
        kw["common_words"] = base.common_words | frozenset(cfg["common_words"])
    return replace(base, **kw)


def load_kb(root: str | Path) -> KB:
    root = Path(root)
    meta = _read(root / "meta.json")
    rel_path = root / "relevance.json"
    spec_name = meta.get("spec", "ko_generic")
    spec_path = root / spec_name
    return KB(root=root, meta=meta, digest=_read(root / "digest.json"), cards=_read(root / "cards.json"),
              personas=_read(root / "personas.json"), relevance=_read(rel_path) if rel_path.exists() else None,
              topic=load_topic(meta.get("topic")), spec=load_spec(str(spec_path) if spec_path.exists() else spec_name))


def llm_from_env() -> JsonLLM:
    """재료 준비용 JSON 호출 — sarangbang 환경 변수 규칙 그대로(SARANGBANG_PROVIDER 또는 SARANGBANG_BASE_URL·_API_KEY·_MODEL)."""
    try:
        return json_llm_from_env()
    except KeyError as e:
        raise SystemExit(str(e).strip("'\"")) from None
