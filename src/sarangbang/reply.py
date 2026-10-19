"""응답 정리 — 텍스트 모드(도구 없이 '보낼 말만')로 받은 답을 말·답장 번호·넘어감으로 나눈다.

정리 항목: 생각 태그, 대화 기록을 그대로 옮겨 적은 줄('#1 경북 남구: …'), (넘어감) 표시, 답장 표시 변형, 여러 말 몰아 쓰기.
"""
from __future__ import annotations

import re


def clean_reply(raw: str, self_name: str = "", all_names: list[str] | None = None) -> tuple[str, int | None, bool, list[str]]:
    """텍스트 답 → (말, 답장 번호, 넘어감 여부, 정리한 항목).
    정리: 생각 태그, 대화 기록을 그대로 옮겨 적은 줄('#1 경북 남구: …'), (넘어감) 표시, 답장 표시 변형, 여러 말 몰아 쓰기."""
    t = (raw or "").strip()
    fixes: list[str] = []
    if "<think>" in t or "</think>" in t:
        t = re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL).replace("</think>", " ").replace("<think>", " ")
        fixes.append("생각 태그")
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    kept, dropped = [], 0
    for ln in lines:
        m = re.match(r"^#\d+\s+(\d{1,2}:\d{2}\s+)?([^:\n]{1,20}):\s*(.*)$", ln)
        if m:
            if m.group(2).strip() in ("나", self_name):  # '#37 관악: 말'(자기 이름으로 기록 꼴)도 자기 말
                kept.append(m.group(3))
                fixes.append("기록 줄머리")
            else:
                dropped += 1  # 남의 줄을 옮겨 적음
            continue
        kept.append(ln)
    if dropped:
        fixes.append(f"옮겨 적은 기록 줄 {dropped}")
    PASS = r"[\(\[]\s*넘어감\s*[\)\]]"
    is_pass_mark = any(re.search(PASS, k) or re.fullmatch(r"\s*넘어감\.?\s*", k) for k in kept)
    kept = [re.sub(PASS, "", k).strip() for k in kept if not re.fullmatch(r"\s*넘어감\.?\s*", k)]
    kept = [k for k in kept if k]
    t = "\n".join(kept).strip()
    reply = None
    names_ = [n for n in (all_names or []) if n]
    # 대괄호 답장 표시 '[#8에 답장]'·'[8에 답장]'·'[#8 동구에 답장]' → 둥근 괄호 꼴로
    t = re.sub(r"^\[\s*#?(\d+)((?:\s+[^\s\]]{1,12}){0,2})\s*(?:에게|에)?\s*답장\s*\]", r"(#\1에 답장)", t)
    # '[이름]' 줄머리로 여러 사람 말을 몰아 쓴 경우 — 자기 이름 묶음, 없으면 줄머리 없는 앞부분만
    if re.search(r"(^|\n)\s*\[[^\]\n]{1,15}\]", t):
        blocks = re.split(r"(?:^|\n)\s*\[([^\]\n]{1,15})\]\s*", t)
        head, pairs = blocks[0].strip(), list(zip(blocks[1::2], blocks[2::2]))
        hdr = [p for p in pairs if p[0].strip() in names_]
        if hdr:
            own = [b for n_, b in hdr if n_.strip() == self_name]
            t = (own[0] if own else head).strip()
            fixes.append("[이름] 줄머리")
            if not t:
                return "", None, True, fixes + ["다른 사람 이름으로 씀"]
    bare = re.sub(r"[\s.,!?~()\[\]'\"“”]+", "", t)
    if bare and any(bare == re.sub(r"\s+", "", n) for n in names_):
        return "", None, True, fixes + ["이름만 보냄"]
    if re.search(r"넘어감", t) and len(t) <= 15:
        return "", None, True, fixes + ["넘어감 변형"]
    if re.search(r"(할|덧붙일|보탤|더할) 말이 없", t) and len(t) <= 60:
        return "", None, True, fixes + ["말 없음 선언"]
    for n in names_:
        if n != self_name and re.match(rf"^{re.escape(n)}\s*:", t):
            return "", None, True, fixes + ["다른 사람 이름으로 씀"]
    if self_name and t.startswith(self_name + ":"):  # '영천: (#10에 답장) …' — 자기 이름 접두
        t = t[len(self_name) + 1:].lstrip()
        fixes.append("자기 이름 접두")
    # 답장 표시 변형: (#43에 답장) · #43에 답장: · #43 마산회원에 답장 · #30 답장) · (#1 경북 남구)
    m = (re.match(r"^\(?\s*#(\d+)(?:\s*[^\s:()#]{1,12}?)?(?:\s+[^\s:()#]{1,12}?)?\s*(?:에게|에)?\s*답장\s*\)?\s*:?\s*", t)
         or re.match(r"^\(\s*#(\d+)(?:\s+[^\s:()#]{1,12}){0,2}\s*\)\s*:?\s*", t)
         or re.match(r"^#(\d+)(?:\s+|$)", t))  # '#15 포항처럼 …'(번호만 앞에) · '#81'(번호만 — 아래에서 넘어감)
    if m:
        reply, t = int(m.group(1)), t[m.end():]
        if not re.fullmatch(r"\(#\d+에\s*답장\)", m.group(0).strip()):
            fixes.append("답장 표시 변형")
    # 한 호출에 답장을 여러 개 몰아 쓴 경우 — 첫 말만
    cut = re.search(r"\n\s*\(?#\d+(?:\s+[^\s:()#]{1,12})?\s*(?:에게|에)?\s*답장", t)
    if cut:
        t = t[:cut.start()]
        fixes.append("여러 말 중 첫 말만")
    t = t.strip().strip('"“”').strip()
    t = re.sub(r"^[.,·:;\-—\s]+", "", t)  # 답장 표시 뒤에 남은 구두점('#3에 답장. …')
    if not t:
        return "", None, True, fixes
    if is_pass_mark:
        fixes.append("넘어감 표시와 말이 함께 옴")
    return t, reply, False, fixes
