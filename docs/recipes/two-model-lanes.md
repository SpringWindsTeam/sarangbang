# 모델 두 개로 나눠 말하기

소식과 가장 가까운 시민 일부(정적 점수 상위 1/6)는 **앵커 레인**의 큰 모델로, 나머지는 **기본 레인**의 빠른 모델로 말하게 합니다. 대화를 이끄는 사람의 발언 품질을 높이면서 전체 속도를 유지하는 구성입니다. 앵커 레인 호출이 실패하면 그 시민은 기본 레인으로 넘어갑니다.

## 명령줄로

```bash
sarangbang run examples/cafe_price.json --msgs 30 \
    --provider vllm --model skt/A.X-4.0-Light --slots 8 \
    --anchor-provider upstage --anchor-model solar-pro4 --anchor-slots 2
```

## 환경 변수로

```bash
export SARANGBANG_PROVIDER=vllm SARANGBANG_MODEL=skt/A.X-4.0-Light          # 기본 레인
export SARANGBANG_ANCHOR_PROVIDER=upstage SARANGBANG_ANCHOR_MODEL=solar-pro4   # 앵커 레인
```

`sarangbang run`과 `examples/kb_tools`는 `SARANGBANG_ANCHOR_*`가 있으면 앵커 레인을 함께 만듭니다.

## 라이브러리로

```python
from sarangbang import get_provider, lane_from_env, run_rooms

lanes = {"anchor": get_provider("upstage").lane("anchor", model="solar-pro4", slots=2),
         "base": get_provider("vllm").lane("base", model="skt/A.X-4.0-Light", slots=8)}
# 또는 환경 변수로: {"anchor": lane_from_env("anchor", prefix="SARANGBANG_ANCHOR"), "base": lane_from_env("base")}
stats = await run_rooms(rooms, lanes)
```

- `slots`는 모든 방이 함께 쓰는 레인별 동시 호출 수입니다.
- 앵커 비율은 `Room(..., anchor_frac=…)`으로 바꿉니다(기본 1/6).
- 어떤 시민이 앵커가 될지는 정적 점수(`scorer`, 시민의 `score`)로 정해집니다. 점수 매기는 법은 [04. 시민 구성하기](../knowledge-base/04-personas.md#점수score와-입장-기울기lean)에 있습니다.
