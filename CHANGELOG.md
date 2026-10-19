# 변경 기록

## 0.1.0 (미공개)

- 첫 공개 준비. 민심(minsim) 교육정책 시뮬레이션의 단톡방 엔진을 독립 패키지로 분리.
- 엔진(`Room`, `run_rooms`), OpenAI 호환 레인(`Lane`, `JsonLLM`), 사양 렌더(`build_room`, 기본 사양 `ko_s12`),
  대화 기록·응답 정리, 쟁점 카드 배분, 카드 관련성·연결 의견·첫 메시지 프롬프트, `PersonaAdapter`·`DictAdapter`.
- 주제 어댑터 `Topic`(입장 문장·관계 항목 이름·준비 프롬프트·주제 일반어) — `POLICY_KO`(교육정책 테스트 문구), `GENERIC_KO`(범용, 기본값).
- 범용 설정 `ko_generic`(기본값) 추가. `ko_s12`는 `POLICY_KO`와 짝.
- 프롬프트 주입 인터페이스 `PromptPlugin`(system_sections · tail · call_context)과 `StaticSections`.
- `NemotronKoreaAdapter`(Nemotron-Personas-Korea 증강판 행 그대로), `affected(p, target)`로 인터페이스 변경, 예제 `nemotron_korea.py`(데이터셋 뷰어 API로 필요한 행만 읽음).
