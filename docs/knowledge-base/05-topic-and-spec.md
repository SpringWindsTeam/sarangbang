# 05. 주제 문구와 사양

## 주제 문구 (Topic)

주제 문구는 소식을 무엇이라고 부를지, 입장 문장을 어떻게 쓸지, 재료 준비 프롬프트를 무엇으로 할지를 정합니다. sarangbang에는 두 가지가 들어 있습니다.

| 이름 | 쓰는 경우 | 상태 |
|---|---|---|
| `POLICY_KO` | 정부·지자체 정책, 제도 변경 | 한국어 교육정책 시뮬레이션에서 비교 시험으로 고른 문구 |
| `GENERIC_KO` | 동네 소식, 가게, 회사 공지, 제품 등 | 정책 낱말을 범용으로 바꾼 문구. 아직 비교 시험 전 |

지식 베이스 폴더에서는 `meta.json`의 `topic` 항목으로 지정합니다.

```json
"topic": {
  "base": "generic",
  "noun": "주차 요금 변경",
  "label": "[동네 소식]",
  "relation_label": "[이 일과 나]",
  "common_words": ["주차", "주차장", "요금"]
}
```

| 항목 | 설명 |
|---|---|
| `base` | `generic`(GENERIC_KO) 또는 `policy`(POLICY_KO) |
| `noun` | 소식을 부르는 말 |
| `label` | 사실 목록 앞에 붙는 머리표 |
| `relation_label` | 시민과 소식의 관계 칸 이름 |
| `common_words` | "이미 여러 사람이 많이 한 말" 집계에서 뺄 낱말. 주제상 누구나 쓰는 낱말(예: 주차, 요금)을 넣습니다 |

`common_words`를 넣지 않으면, 모두가 당연히 쓰는 낱말(예: "주차 요금")이 반복 표현으로 잡혀 시민에게 "이미 많이 나온 말"로 안내됩니다. 그러면 정작 그 소식 얘기를 피하게 됩니다.

코드로 쓸 때는 `dataclasses.replace(GENERIC_KO, ...)`로 만듭니다([`examples/kb_tools/kb.py`](../../examples/kb_tools/kb.py)의 `load_topic` 참고). sarangbang 시나리오 파일(`sarangbang run`)은 `generic`/`policy` 선택만 받으므로, 머리표·관계 칸 이름·`common_words`를 바꾸려면 `kb_tools.run`을 씁니다.

## 사양 (spec)

사양은 프롬프트의 칸 이름, 문구, 켜고 끄는 항목을 담은 JSON입니다. `meta.json`의 `spec`으로 지정합니다.

| 이름 | 짝이 되는 주제 문구 |
|---|---|
| `ko_s12` | `policy` |
| `ko_generic` | `generic` |

두 사양은 칸 구성이 같고 정책 낱말만 다릅니다. 자기 사양이 필요하면 sarangbang의 `specs/ko_generic.json`을 복사해 고친 뒤 파일 경로를 `spec`에 적습니다.

### 범용 사양을 정책이 아닌 소식에 쓸 때

`ko_generic`의 가벼운 찬성 말투(`light_support`)는 새로 생기는 일을 반기는 문구라, 가격 인상이나 논란처럼 이미 일어난 일에는 어색하게 붙을 수 있습니다. 그럴 때는 해당 시민에게 `steady: true`를 주거나, 사양 JSON을 복사해 그 칸을 고칩니다.

### 사양을 고칠 때

사양 문구를 고치는 방법과 시험 기준은 [CONTRIBUTING.md](../../CONTRIBUTING.md)를 따릅니다. 이 문서들은 사양을 그대로 두고 지식 베이스를 바꾸는 방법을 다룹니다.

## 모델 고르기

프롬프트 사양과 응답 정리는 EXAONE·A.X의 한국어 응답을 기준으로 맞춰져 있습니다. 어디서 모델을 받아 쓸지는 [국산 AI 모델 사용 가이드](../korean-ai-providers.md)를 봅니다. `sarangbang models`는 오픈 웨이트 국산 모델과 추론 모드 끄는 법을, `sarangbang providers`는 쓸 수 있는 제공처를 보여 줍니다.
