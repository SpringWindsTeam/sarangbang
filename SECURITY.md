# 보안 정책 (Security Policy)

## 지원 버전

| 버전 | 보안 패치 |
|---|---|
| 0.2.x | ✅ |
| < 0.2 | ❌ |

## 취약점 보고

sarangbang은 사용자가 지정한 OpenAI 호환 엔드포인트로 HTTP 요청을 보내는 라이브러리입니다. 다음과 같은 문제는 **공개 이슈 대신**
비공개로 알려 주세요.

- API 키가 로그·결과 파일·예외 메시지에 노출되는 경우
- 시나리오·응답 JSON 처리에서 임의 코드 실행이나 경로 탈출이 가능한 경우
- 의존성(`httpx`)의 알려진 취약점이 영향을 주는 경우

### 보고 채널

- GitHub Private Vulnerability Report: https://github.com/springwindteam/sarangbang/security/advisories/new
- 이메일: spring.wind.team@gmail.com (제목에 `[sarangbang security]`)

### 포함하면 좋은 것

1. 영향 받는 버전과 환경(OS, Python)
2. 재현 절차(최소 코드 — 실제 API 키나 실제 사람의 데이터는 넣지 않습니다)
3. 예상 영향

### 응답 일정 (best-effort)

- 접수 확인: 영업일 기준 3일 이내
- 영향 평가와 패치 계획: 14일 이내
- 패치·권고문 공개: 심각도에 따라 조율

## 안전하게 쓰기

- API 키는 환경 변수로만 전달하세요(`UPSTAGE_API_KEY`, `SARANGBANG_API_KEY` …). 시나리오 파일이나 결과 파일에 키를 적지 마세요.
- `sarangbang run --out`이 저장하는 결과에는 모델 원본 응답(`calls[].raw`)이 들어갑니다. 공유하기 전에 내용을 확인하세요.
- 시민 데이터는 합성 데이터(예: Nemotron-Personas-Korea 증강판)를 권장합니다. 실제 사람의 글·닉네임을 페르소나로 쓰지 마세요.
