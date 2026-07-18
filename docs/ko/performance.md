# 성능 튜닝 (Pi 4B 4GB)

Pi 4B는 작업 세트를 작게 유지하면 3~4명 서바이벌 월드를 매끄럽게 돌릴 수 있습니다.
목표는 안정적인 **20 TPS**(초당 틱)입니다.

## 큰 지렛대 (영향 순)

1. **`view-distance` / `simulation-distance`**(`server.properties`). 낮출수록
   로드/틱되는 청크가 줄어듭니다. `view-distance=8`, `simulation-distance=6`으로
   시작하고, 전원 접속 시 렉이 있으면 `6`/`4`로 낮추세요. TPS에는 시뮬레이션
   거리가 가장 중요합니다.
2. **스토리지.** 월드는 SD카드가 아니라 **USB 3.0 저장장치**를 쓰세요. SSD가 가장
   빠르지만 3~4명 서버는 500GB HDD도 사용할 수 있습니다. SD카드의 랜덤
   쓰기가 파이의 가장 흔한 병목이며 틱 멈춤을 유발합니다.
3. **메모리.** `MC_MEMORY=2600M`(고정 Xms=Xmx)이 OS+봇 여유를 남깁니다. 과할당
   금지 — 파이는 GPU/OS와 공유하는 4GB뿐입니다.
4. **플레이어 수.** `max-players`는 작게(6). 플레이어마다 청크를 로드합니다.

## JVM / GC

`scripts/start_server.sh`는 **Aikar 플래그**(마인크래프트용으로 튜닝된 G1GC)에
`AlwaysPreTouch`와 고정 힙을 씁니다. GC 멈춤을 최소화하는데, 파이에서 이는 끊김으로
체감됩니다. OS용 ~1~1.5GB를 남기는 선을 넘겨 힙을 키우지 마세요.

## PaperMC 월드 튜닝

Paper는 `config/paper-world-defaults.yml`에 조절 항목을 노출합니다. 파이 친화적
변경:

- 농장이 렉을 유발하면 **몹 캡/스폰 범위 축소**:
  `entities.spawning.per-player-mob-spawns: true`(기본 true)가 도움.
- **`ticks-per.hopper-transfer`** / 호퍼 검사 — 큰 농장의 호퍼 부하를 줄이려면
  약간 올리기.
- **`chunks.max-auto-save-chunks-per-tick`** — 저장 스파이크를 완만하게 낮추기.
- 아이템 병합/제한: `tick-inactive-villagers`와 아이템 병합 반경으로 엔티티 수 감소.

변경 후 재시작. 한 번에 하나씩 바꾸고 TPS를 지켜보세요.

## 무인 절전 (빈 서버, #91)

접속자가 없어도 월드는 계속 틱합니다 — 스폰 청크가 로드된 채 틱하고, 블록 랜덤
틱(작물 성장·잎 부패·불 번짐)도 계속 돌아 Pi의 CPU·발열·전력을 낭비합니다. 봇이
빈 서버를 감지해 잠깐의 유예 시간 뒤 이 유휴 작업을 잠재웠다가, 플레이어가
접속하는 즉시 되돌립니다.

- 비었을 때 `randomTickSpeed` → `0`(블록 랜덤 틱 정지), 접속 시 복원.
- 비었을 때 `spawnChunkRadius` → `0`(스폰 청크 틱 정지), 접속 시 복원. 이 게임룰은
  마인크래프트 1.20.5+ 전용으로, 구버전에서는 자동으로 건너뜁니다.

봇은 **값을 바꾸기 전에 현재 값을 먼저 읽어** 그대로 복원하므로, 운영자가 손수
바꿔 둔 설정을 덮어쓰지 않습니다. Pi의 추적용 `.env`에서 설정합니다:

- `IDLE_ECO_ENABLED` — `true`/`false` (기본 `true`).
- `IDLE_ECO_AFTER_MINUTES` — 절전에 들어가기 전 서버가 비어 있어야 하는 시간(분,
  기본 `10`).

이것은 어디까지나 *유휴* 부하만 줄입니다. 무거운 작업은 플레이어가 있을 때
발생하므로, 위의 정적 지렛대(메모리, 뷰/시뮬레이션 거리, 냉각)도 함께 잘
관리하세요.

## 모니터링

Discord `/관리자`의 **성능** 버튼은 Paper TPS, Pi CPU 온도,
1/5/15분 load average, 메모리, HDD, 업타임, 현재·과거 저전압/스로틀링 비트를
한 화면에 표시합니다.

SSH에서는 다음 명령으로 서비스·HDD·자원·RCON을 함께 확인합니다.

```bash
./scripts/health_check.sh
```

- 게임/RCON: `tps`(Paper)로 최근 TPS, `mspt`로 틱당 ms 확인.
- OS: `htop`, `vcgencmd measure_temp`(온도), `iostat`(디스크).
- 파이를 **시원하게** — 뜨거우면 스로틀링으로 TPS가 떨어집니다. 특히 케이스에
  넣는다면 히트싱크+팬을 쓰세요.

## 증상 → 해결

| 증상 | 유력 원인 | 해결 |
|---|---|---|
| 주기적 멈춤 | 저장장치 쓰기 정체 | USB 3.0 확인, 월드 사전 생성 또는 SSD 고려 |
| 몹 많을 때 낮은 TPS | 과한 시뮬레이션 | `simulation-distance`·몹 캡 낮추기 |
| 접속/탐험 시 렉 | SD에서 청크 생성 | SSD; 플러그인으로 사전 생성 |
| 시간 지날수록 렉 증가 | 열 스로틀링 | 냉각; `vcgencmd measure_temp` 확인 |
| GC 끊김 | 힙 과대/과소 | `MC_MEMORY` ~2600M, Aikar 플래그 유지 |
