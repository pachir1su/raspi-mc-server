# 치트와 관리자 — "나만 치트"

## 핵심 개념

싱글플레이 마인크래프트에는 월드별 **치트 허용** 스위치가 있습니다. 멀티플레이
서버에는 **없습니다**. 서버에서 치트 명령(`/gamemode`, `/give`, `/time set`,
`/tp` …) 사용 여부는 **관리자(op)** 인지로 결정됩니다.

- **op 아님** → 치트 명령을 아예 쓸 수 없음.
- **op** → `op-permission-level`(4 = 전부)까지 사용 가능.

그래서 "맵은 치트 끄고 나만 치트"는 간단한 규칙으로 달성됩니다:

> **나만 op로. 다른 누구도 op 하지 않기.**

친구들은 명령 접근 없이 일반 서바이벌을 즐기고, 나는 완전한 통제권을 유지합니다.

## 나만(정확히 나만) op 하기

서버 콘솔이나 Discord `/관리자` 첫 화면(또는 **고급 도구**)의 **인게임 명령어**에서:

```
op 내마크닉네임
```

다른 사람이 op가 아닌지 확인하세요 — `server/ops.json`에는 항목이 딱 하나(나)여야
합니다. 예시는 `server/ops.json.example`에 있습니다.

실수로 준 op 회수:

```
deop 다른사람
```

## 그래도 내가 원격으로 치트할 수 있는 이유

**콘솔·RCON·디스코드 봇·SSH 세션**은 ops 목록과 무관하게 항상 **op 레벨 4**로
명령을 실행합니다. 그래서:

- Discord **인게임 명령어**은 어떤 명령이든 실행합니다(RCON 경유).
- SSH의 `.venv/bin/python -m bot.rcon`도 `.env`를 읽어 어떤 명령이든 실행합니다.

이 경로들은 **나에게만**(관리자 허용목록 / SSH 접근 / 콘솔 앞) 열려 있어, 사실상
*나만의* 치트 콘솔이 됩니다 — 게임 안에서 내가 op이기도 하지만요.

## 커맨드 블록 & 함수 레벨

- `enable-command-block=false`(템플릿 기본)는 비-op가 명령을 트리거하는 또 다른
  경로를 없애고 부하를 약간 줄입니다. 빌드에 커맨드 블록이 필요할 때만 켜세요 —
  커맨드 블록은 `op-permission-level`로 실행됩니다.
- `function-permission-level=2`는 데이터팩 함수의 권한을 제한합니다.

## 내 마인크래프트 `/gamemode` 관련 메모

op인 나는 언제든 `/gamemode creative`로 크리에이티브가 될 수 있습니다 — 의도된
"소유자 치트"입니다. 친구들(비-op)은 못 하며, 그게 핵심입니다.

## 자주 쓰는 소유자 치트 명령(콘솔 / Discord 인게임 명령어)

```
gamemode creative 내닉네임
gamemode survival 내닉네임
time set day
weather clear
give 내닉네임 minecraft:elytra
tp 내닉네임 0 100 0
difficulty peaceful
```
