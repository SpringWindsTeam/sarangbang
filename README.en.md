**English** | [한국어](README.md)

<div align="center">

<img src="assets/logo.svg" width="112" alt="sarangbang logo">

# 사랑방 sarangbang

**Korean group-chat public-opinion simulation engine for LLM personas**

[![PyPI](https://img.shields.io/pypi/v/sarangbang.svg)](https://pypi.org/project/sarangbang/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![CI](https://github.com/SpringWindsTeam/sarangbang/actions/workflows/ci.yml/badge.svg)](https://github.com/SpringWindsTeam/sarangbang/actions/workflows/ci.yml)
[![Dataset](https://img.shields.io/badge/🤗%20dataset-Nemotron--Personas--Korea%20augmented-yellow)](https://huggingface.co/datasets/springwindteam/nemotron-personas-korea-augmented)

</div>

**sarangbang** simulates public opinion as conversation. LLM personas chat in small Korean group-chat rooms (*danthokbang*)
about a topic — a policy, a product, a neighborhood issue — and the transcript is the output. It was built for Korean models
(LG AI Research's **EXAONE**, SK Telecom's **A.X**) and ships presets for every major way to run Korean AI today.

## Install

```bash
pip install sarangbang
sarangbang quickstart --fake          # no network: a 4-persona toy room with canned replies
```

## Connect a Korean model

sarangbang talks to any OpenAI-compatible `/chat/completions`. Presets cover the three ways to use Korean models
(details and licenses: [docs/korean-ai-providers.md](docs/korean-ai-providers.md), Korean):

| Route | Preset | Example |
|---|---|---|
| Korean vendor APIs | `upstage` (Solar), `clova` (NAVER HyperCLOVA X) | `UPSTAGE_API_KEY=… sarangbang quickstart --provider upstage` |
| Gateways | `friendli`, `openrouter` | `sarangbang doctor --provider openrouter --model upstage/solar-mini4` |
| Self-hosted open weights | `vllm`, `sglang`, `ollama`, `lmstudio` | `ollama pull exaone3.5:7.8b && sarangbang quickstart --provider ollama --model exaone3.5:7.8b` |

```bash
sarangbang providers     # where Korean AI is available + env var names
sarangbang models        # open-weight Korean models (EXAONE, K-EXAONE, A.X, Solar Open, HyperCLOVA X SEED, Kanana, Mi:dm …) with vllm serve hints
sarangbang doctor        # check key / URL / model with one short call
sarangbang run examples/cafe_price.json --provider vllm --model skt/A.X-4.0-Light --msgs 60 --out run.json
```

Presets send only the sampling arguments each server accepts (CLOVA Studio rejects `presence_penalty`; local servers get
`chat_template_kwargs.enable_thinking=false` so reasoning models answer in plain text).

## How it works

- **Stateless calls.** Every call is `system` (persona facts + spec sections) + `user` (the chat transcript rendered as it would
  appear on screen). No agent memory, no rounds.
- **Async rooms.** Many rooms share per-lane concurrency limits. One in-flight call per persona; late replies get an automatic reply-to.
- **Deterministic speaker order.** A data-driven static score plus recency, replies, passes and waiting time. No randomness in the engine.
- **Two lanes.** The top-scored personas (anchors) use a stronger model; the rest use a fast one; failed anchor calls fall back.
- **Spec JSON.** Prompt sections and wording live in one JSON file. The bundled `ko_s12` spec was selected by comparative tests on
  Korean education-policy simulations; `ko_generic` is the topic-neutral default.
- **Topic adapter.** Stance sentences, the relation-section label and the preparation prompts depend on the topic and live in `Topic`
  (`POLICY_KO`, `GENERIC_KO`, or your own).
- **Prompt plugins.** `PromptPlugin` adds system sections, a closing tail, or per-call context without editing the spec.
- **Bring your own personas.** Records are opaque to the engine. Implement `PersonaAdapter` for your schema, or use the bundled
  `NemotronKoreaAdapter` for [Nemotron-Personas-Korea — Augmented](https://huggingface.co/datasets/springwindteam/nemotron-personas-korea-augmented),
  1M synthetic Korean personas (CC BY 4.0) released by the same team (Team Chunpung).
- **Scenario files.** Put the topic, facts, issue cards and personas in one JSON and run it with `sarangbang run` or `load_scenario()`.
- **Model-specific post-processing.** `clean_reply` strips `<think>` tags, copied transcript lines, malformed reply markers and
  multi-speaker answers that small Korean models tend to produce.

```python
import asyncio
from sarangbang import get_provider, load_scenario, run_rooms
from sarangbang import scenario as S

d = load_scenario("toy_library")                   # or "my_scenario.json"
prep = S.prepare(d)                                # allocate cards → per-persona prompts (no LLM)
lane = get_provider("vllm").lane("base", model="skt/A.X-4.0-Light", slots=4)
room = S.make_room(d, prep, S.seed_share(d, prep, get_provider("vllm").json_llm(model="skt/A.X-4.0-Light")), target_msgs=40)
stats = asyncio.run(run_rooms([room], {"base": lane}, on_message=lambda r, m: print(S.format_line(r, m))))
```

The full engine reference (Room, lanes, spec JSON keys, Topic, PromptPlugin, PersonaAdapter, result format) is in the Korean README.

## Why not CAMEL / OASIS?

Each call must carry exactly the context we choose — no accumulated memory, no English wrappers — because Korean models copied
earlier messages and invented family members when fed long agent memories. The engine owns the transcript (`Room.msgs`) and
re-renders it every call.

## Contributing · Citation · License

See [CONTRIBUTING.md](CONTRIBUTING.md) (Korean). Prompt-wording changes need a before/after comparison under the same conditions.
Cite with [CITATION.cff](CITATION.cff). Licensed under [Apache-2.0](LICENSE); see [NOTICE](NOTICE).
