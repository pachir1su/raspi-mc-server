# 서버장 운영 런북

라즈베리파이 4B + 32GB microSD + 500GB USB HDD 구성을 운영할 때 쓰는
점검·업데이트·장애 대응 순서입니다. 평소에는 Discord `/panel`을 사용하고,
Discord나 봇이 작동하지 않을 때만 SSH 명령을 사용합니다.

## 일상 점검

Discord에서 `/panel`을 열고 다음을 확인합니다.

1. 서버 온라인 상태.
2. HDD 여유 공간.
3. 최근 백업이 설정 주기의 2배보다 오래되지 않았는지.
4. **성능** 버튼의 TPS, CPU 온도, 메모리, 전원·스로틀 상태.

| 항목 | 정상 | 주의 |
|---|---|---|
| TPS | 19~20 | 18 미만이 반복됨 |
| CPU 온도 | 70°C 미만 | 80°C 이상 |
| 메모리 | 85% 미만 | 90% 이상 지속 |
| HDD | 30GB 이상 여유 | 설정한 최소 여유 미만 |
| 전원·스로틀 | `정상` | 현재 저전압/스로틀링 |

SSH에서 같은 내용을 확인하려면:

```bash
cd ~/raspi-mc-server
./scripts/health_check.sh
```

## 서버 시작·정지·재시작

- 일반 작업: `/panel` → **서버 제어**.
- 정지·재시작은 확인 버튼을 한 번 더 누릅니다.
- Discord가 안 되면:

```bash
sudo systemctl status minecraft.service mc-discord-bot.service
sudo systemctl restart minecraft.service
sudo systemctl restart mc-discord-bot.service
```

정지 버튼은 먼저 `save-all flush`를 시도합니다. 강제 종료나 정전 뒤에는 최신
로그와 백업 무결성을 확인한 후 플레이를 재개하세요.

## 플레이어 지원

`/players`에서 접속자를 선택한 뒤 인벤토리, 좌표·차원, 체력·허기·경험치,
상태 효과를 확인합니다. 이 기능은 읽기 전용이며 오프라인 플레이어의 라이브
엔티티 데이터는 RCON으로 조회할 수 없습니다.

## 로그 확인 순서

1. `/logs` → **마크 오류**.
2. 봇 명령 문제면 **봇 오류**.
3. 문맥이 부족하면 전체 미리보기.
4. 필요하면 원본 파일 다운로드.
5. Discord 한도를 넘으면 SSH에서 확인.

```bash
sudo journalctl -u minecraft.service -n 200 --no-pager
sudo journalctl -u mc-discord-bot.service -n 200 --no-pager
tail -n 200 /mnt/minecraft/live/logs/latest.log
```

## HDD가 사라졌을 때

증상: `/storage` 실패, systemd 서비스 시작 실패, `/health` 마운트 오류.

```bash
lsblk -f
findmnt /mnt/minecraft
sudo journalctl -b -u mnt-minecraft.mount --no-pager
sudo mount /mnt/minecraft
```

1. USB 케이블과 HDD 전원을 확인합니다.
2. `lsblk -f`에서 기존 UUID가 보이는지 확인합니다.
3. 장치명이 달라져도 `/etc/fstab`은 UUID 기반이므로 임의 수정하지 않습니다.
4. `/mnt/minecraft/live`가 실제 서버 데이터인지 확인합니다.
5. 그 뒤에만 Minecraft와 봇 서비스를 시작합니다.

HDD가 마운트되지 않은 상태에서 `/mnt/minecraft` 아래에 파일을 만들면 microSD의
빈 마운트 디렉터리에 운영 데이터가 섞일 수 있습니다.

## 저전압·스로틀링 경고

`/metrics` 또는 다음 명령을 확인합니다.

```bash
vcgencmd get_throttled
vcgencmd measure_temp
```

- **현재 저전압**: 전원 어댑터·케이블·HDD 전력 공급을 즉시 점검.
- **과거 저전압**: 이력 비트가 남을 수 있으므로 반복 여부 관찰.
- **현재 온도 제한/스로틀링**: 팬, 방열판, 통풍, 주변 온도 확인.

## 백업과 복구

복구 전 `/backup verify`로 검사하고, 중요한 백업을 다른 장치에도 복사한 뒤,
접속자에게 정지를 알리고 `/backup restore`를 실행합니다. 복구는 현재 월드를 다시
비상 백업하지만 같은 HDD의 백업은 HDD 자체 고장을 막지 못합니다.

## 안전한 업데이트

```bash
cd ~/raspi-mc-server
git status --short
git fetch origin
git switch main
git pull --ff-only
.venv/bin/pip install -r requirements.txt
sudo ./deploy/setup_raspberrypi.sh
sudo systemctl restart minecraft.service mc-discord-bot.service
./scripts/health_check.sh
```

예상하지 못한 로컬 변경은 덮어쓰지 말고 먼저 백업합니다. 업데이트 후 `/panel`,
`/metrics`, `/logs`, 수동 백업을 각각 확인하세요.

## 기기 밖에 보관할 것

- 최근 검증 완료 월드 백업 여러 개
- 실제 `.env` 운영 값(공개 저장소가 아닌 비밀 저장소)
- `/mnt/minecraft/live/server.properties`
- Discord 애플리케이션 복구 정보

실제 토큰, RCON 비밀번호, 월드 파일은 Git에 커밋하지 않습니다.
