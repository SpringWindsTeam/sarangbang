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
"""
from .cards import allocate, hearsay_fill, kept
from .engine import Room, parse_text, run_rooms
from .llm import FakeLane, JsonLLM, Lane
from .log import render_log, saturated_terms
from .persona import DictAdapter, PersonaAdapter
from .plugins import PromptPlugin, StaticSections
from .reply import clean_reply
from .scene import KO, Scene
from .spec import PersonPrompt, build_room, load_spec
from .stance import stance_line
from .topic import GENERIC_KO, POLICY_KO, Topic, TopicAdapter

__version__ = "0.1.0"

__all__ = [
           "GENERIC_KO",
           "POLICY_KO",
           "PromptPlugin",
           "StaticSections",
           "Topic",
           "TopicAdapter",
           "KO",
           "DictAdapter",
           "FakeLane",
           "JsonLLM",
           "Lane",
           "PersonPrompt",
           "PersonaAdapter",
           "Room",
           "Scene",
           "__version__",
           "allocate",
           "build_room",
           "clean_reply",
           "hearsay_fill",
           "kept",
           "load_spec",
           "parse_text",
           "render_log",
           "run_rooms",
           "saturated_terms",
           "stance_line",
]
