# 서버 설정

서버는 기본적으로 `/mnt/minecraft/live/server.properties`를 읽습니다. 이 저장소는 파이 친화적·친구 전용
기본값이 들어간 `server/server.properties.template`을 제공합니다. 아래는 가장
중요한 항목들이며, 템플릿 주석에 각 항목 설명이 있습니다.

## 접근 제어

| 키 | 기본값 | 이유 |
|---|---|---|
| `white-list` | `true` | 등록된 사람만 입장. |
| `enforce-whitelist` | `true` | 실행 중 등록돼도 비화이트리스트는 강제 퇴장. |
| `online-mode` | `true` | Mojang 계정 검증(켜 두기). |
| `max-players` | `6` | 3~4명보다 약간 여유; 파이에선 작게. |
| `op-permission-level` | `4` | op는 모든 명령 접근. |
| `enable-command-block` | `false` | 비-op 명령 경로 축소 + 부하 약간 절감. |

## 성능 키(파이 핵심)

| 키 | 기본값 | 메모 |
|---|---|---|
| `view-distance` | `8` | 가장 큰 지렛대. 렉이면 `6`, 여유면 `10`. |
| `simulation-distance` | `6` | 엔티티/레드스톤 틱 범위. view-distance 이하로. |
| `network-compression-threshold` | `256` | LAN에선 무난; 느린 WAN에서만 낮추기. |
| `sync-chunk-writes` | `false` | 파이 스토리지에서 처리량 향상. |

자세히는 [performance.md](performance.md).

## RCON

RCON으로 디스코드 봇과 CLI가 실행 중인 서버에 명령을 보냅니다.

```properties
enable-rcon=true
rcon.port=25575
rcon.password=<강력한 비밀값 — 파이에서만 설정, 절대 커밋 금지>
broadcast-rcon-to-ops=false
```

`rcon.port`는 localhost에 두세요(봇 기본 접속 호스트는 `127.0.0.1`). `25575`를
인터넷에 **포워딩하지 마세요**. [remote-access.md](remote-access.md) 참고.

## 난이도 & 게임플레이

`gamemode`, `difficulty`, `pvp`, `hardcore`, `allow-nether`는 합리적인 서바이벌
기본값입니다. 취향대로 바꾸고, 적용하려면 서버를 재시작하세요(또는 봇의 `/restart`).

## 변경 적용

대부분의 `server.properties` 변경은 재시작이 필요합니다:

```bash
sudo systemctl restart minecraft.service   # 또는 디스코드 봇 /restart
```

## Paper 전용 튜닝

PaperMC는 `config/paper-global.yml`, `config/paper-world-defaults.yml`,
`spigot.yml`/`bukkit.yml`을 추가합니다. 기본값이 좋으며, 파이용 엔티티/몹 튜닝은
[performance.md](performance.md)를 보세요.
