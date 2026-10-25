"""sarangbang — 한국어 단톡방 여론 시뮬레이션 엔진.

가상 시민 여럿이 작은 단톡방에서 어떤 소식(정책·제품·동네 일 …)을 두고 비동기로 대화한다. 라운드·에이전트 기억 없이, 매 호출은
system(시민 사실·사양 칸) + user(단톡방 화면 그대로의 대화 기록) 두 메시지의 독립 호출이다.

층
- engine: 방·발언 순위·레인 공유 스케줄러(Room, run_rooms)
- llm: OpenAI 호환 레인(Lane)·JSON 호출(JsonLLM)·시험용 FakeLane
- spec: 프롬프트 사양 JSON 렌더(build_room) · scene/log/reply/stance: 장면·대화 기록·응답 정리·입장 문장
- cards / material: 쟁점 카드 배분 · 카드 관련성·연결 의견·첫 메시지(LLM)
- persona: 시민 레코드 어댑터(PersonaAdapter)와 간단한 DictAdapter
- topic: 주제 어댑터(Topic — 입장 문장·관계 칸·재료 프롬프트), POLICY_KO·GENERIC_KO
- plugins: 프롬프트 주입 인터페이스(PromptPlugin — 시스템 칸·마무리 앞 꼬리·호출별 문맥)
- providers: 국산 AI를 쓸 수 있는 곳의 프리셋(Provider, get_provider, lane_from_env)과 오픈 웨이트 모델 목록(OPEN_MODELS)
- scenario: 주제·시민·카드를 담은 JSON 하나로 방을 돌리는 도우미(load_scenario, prepare, make_room) — CLI `sarangbang run`
"""
from .cards import allocate, hearsay_fill, kept
from .engine import Room, parse_text, run_rooms
from .llm import FakeLane, JsonLLM, Lane, LLMError
from .log import render_log, saturated_terms
from .persona import DictAdapter, PersonaAdapter
from .plugins import PromptPlugin, StaticSections
from .providers import OPEN_MODELS, PROVIDERS, OpenModel, Provider, get_provider, json_llm_from_env, lane_from_env
from .reply import clean_reply
from .scenario import load_scenario
from .scene import KO, Scene
from .spec import PersonPrompt, build_room, load_spec
from .stance import stance_line
from .topic import GENERIC_KO, POLICY_KO, Topic, TopicAdapter

__version__ = "0.2.0"

__all__ = [
           "GENERIC_KO",
           "OPEN_MODELS",
           "POLICY_KO",
           "PROVIDERS",
           "PromptPlugin",
           "StaticSections",
           "Topic",
           "TopicAdapter",
           "KO",
           "DictAdapter",
           "FakeLane",
           "JsonLLM",
           "LLMError",
           "Lane",
           "OpenModel",
           "PersonPrompt",
           "PersonaAdapter",
           "Provider",
           "Room",
           "Scene",
           "__version__",
           "allocate",
           "build_room",
           "clean_reply",
           "get_provider",
           "hearsay_fill",
           "json_llm_from_env",
           "kept",
           "lane_from_env",
           "load_scenario",
           "load_spec",
           "parse_text",
           "render_log",
           "run_rooms",
           "saturated_terms",
           "stance_line",
]
