# 연애 예능 시청자 단톡방

가상의 연애 예능 한 회를 두고 시청자 7명이 "누구와 누가 될까"를 이야기하는 단톡방을 돌려 봅니다. 찬반이 아니라 여러 갈래의 예측이 맞서는 주제를 다루는 예입니다. 방송 내용은 지어낸 것이고, 지식 베이스는 [`examples/knowledge-bases/dating-show`](../../examples/knowledge-bases/dating-show)에 있습니다. README 맨 위 데모 화면이 이 지식 베이스로 실행한 결과입니다.

## 1. 실행

```bash
cd examples
python -m kb_tools.run knowledge-bases/dating-show --fake --msgs 12      # 모델 없이 흐름만
python -m kb_tools.run knowledge-bases/dating-show --msgs 24             # 실제 모델 (SARANGBANG_* 환경 변수)
```

## 2. 대화 읽기

결과는 `out/dating-show/messages.jsonl`에 한 줄에 메시지 하나로 저장됩니다.

```bash
python -c "import json; [print(m['id'], m['name'], m['text']) for m in map(json.loads, open('out/dating-show/messages.jsonl'))]"
```

시청자마다 다른 예측에서 출발하지만, 대화가 진행되면서 서로의 말에 반박하거나 넘어가고, 카드에 없던 해석이 나오기도 합니다.

## 내 버전 만들기

- **예측을 바꾸기**: `personas.json`의 `relation`에 시청자마다 다른 예측을 적습니다("정숙이 막판에 판을 뒤집을 거라고 본다"). 입장 기울기(`lean`)는 비워 둡니다.
- **이론을 늘리기**: `cards.json`에 커플 이론을 카드로 추가합니다. 카드는 서로 다른 시민에게 한 장씩 배분됩니다.
- **회차 진행**: 다음 회 사실을 `digest.json`에 추가하고 다시 돌리면, 같은 시청자들이 새 장면을 두고 이야기합니다.

왜 예측을 입장 대신 사실 칸으로 주는지는 지식 베이스 폴더의 [README](../../examples/knowledge-bases/dating-show/README.md)에 있습니다.
