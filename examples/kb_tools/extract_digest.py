"""소식 원문(공지·보도자료·기사·제품 페이지 등) → 주제 정보(digest.json). 기준은 docs/02-digest.md.

    python -m kb_tools.extract_digest 원문.txt -o knowledge-bases/my-topic/digest.json --title "공영주차장 야간 유료화"
    python -m kb_tools.extract_digest 원문.txt -o digest.json --title "..." --statuses "공식 발표,출시 예정,유출·루머,이전 모델"

--statuses를 주지 않으면 기본 상태 어휘(확정·시행 / 계획·목표 / 과거 실적 / 검토)를 쓴다.
이 프롬프트는 비교 시험을 거치지 않은 출발점이다. 결과는 반드시 사람이 원문과 대조해 검수한다.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .kb import STATUSES, llm_from_env

# 기본 어휘의 판정 기준. 도메인 어휘를 쓰면 "원문 표현에 맞는 것"만 지시한다.
DEFAULT_RULES = """  · 확정·시행: 날짜·대상·금액이 정해졌거나 이미 시행·판매 중(예: '12월 1일부터 부과', '판매합니다')
  · 계획·목표: '~할 예정', '~할 계획', '목표'
  · 과거 실적: 이미 있었던 일, 지난 통계
  · 검토: '검토', '논의', '추후 결정'"""


def system_prompt(statuses: tuple[str, ...]) -> str:
    rules = DEFAULT_RULES if tuple(statuses) == STATUSES else (
        "  · 원문 표현에 비추어 가장 맞는 것 하나. 공식으로 확인되지 않은 내용(소문·추측)은 확인된 것으로 올리지 않는다.")
    return f"""너는 소식 원문(공지·보도자료·기사·제품 페이지 등)에서, 이 소식을 두고 대화할 사람들에게 알려 줄 사실만 골라 정리한다.
규칙
- 읽는 사람에게 무엇이 달라지거나 새로 알려졌는지에 답하는 사실만 고른다. 배경 설명·홍보 문구·작성 기관의 절차는 뺀다.
- 사실 하나에 내용 하나. 가격·혜택·일정처럼 다른 내용은 따로 쓴다.
- 사실마다 시기와 대상을 문장 안에 넣는다. 수치·날짜·이름은 원문 그대로 옮긴다. 원문에 없는 날짜를 계산해 넣지 않는다.
- 문장은 '~한다' '~이다'로 끝낸다.
- status는 {' / '.join(statuses)} 중 하나를 사실마다 원문 표현으로 정한다.
{rules}
- condition은 그 사실이 일부 사람에게만 해당할 때 그 사람들만 적는다(예: 희망자, 기존 가입자, 사전 예약자). 모두에게 해당하면 빈 문자열. 장소·시간은 condition에 넣지 않는다(문장 안에 쓴다).
- 원문이 허락하는 만큼 8~12개. 가장 중요한 사실을 앞에 둔다.
- 원문에 없는 내용은 쓰지 않는다.
JSON으로만 답한다: {{"summary": "두 문장 이내 요약", "facts": [{{"statement": "...", "condition": "...", "status": "{' | '.join(statuses)}"}}]}}"""


def extract(llm, title: str, text: str, statuses: tuple[str, ...] = STATUSES) -> dict:
    d, _ = llm(system_prompt(statuses), f"[제목] {title}\n[원문]\n{text}", max_tokens=3000)
    facts = [f for f in d.get("facts") or [] if f.get("statement")]
    for f in facts:
        f.setdefault("condition", "")
        if f.get("status") not in statuses:
            f["status"] = statuses[-1]       # 판단 못 한 상태는 목록의 마지막 값으로 — 검수 때 확인
    return {"summary": d.get("summary", ""), "facts": facts}


def main() -> None:
    ap = argparse.ArgumentParser(description="소식 원문에서 주제 정보 뽑기")
    ap.add_argument("source", help="원문 텍스트 파일(UTF-8)")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--statuses", help="쉼표로 구분한 상태 어휘(meta.json의 statuses와 같게). 없으면 기본 어휘")
    a = ap.parse_args()
    statuses = tuple(x.strip() for x in a.statuses.split(",") if x.strip()) if a.statuses else STATUSES
    text = Path(a.source).read_text(encoding="utf-8")
    if len(text) > 20000:
        print(f"원문이 {len(text):,}자입니다. 장 단위로 나눠 뽑은 뒤 합치는 편이 안정적입니다.")
    digest = extract(llm_from_env(), a.title, text, statuses)
    Path(a.out).write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"사실 {len(digest['facts'])}개 → {a.out}. 수치와 status를 원문과 대조해 검수하세요.")


if __name__ == "__main__":
    main()
