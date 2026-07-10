# 백업

`scripts/backup.sh`는 월드 폴더(`world`, `world_nether`, `world_the_end`)를
`backups/` 아래 타임스탬프가 붙은 `.tar.gz`로 스냅샷하고, SD카드가 가득 차지
않도록 회전 보관합니다.

## 실행 중 서버의 안전한 백업

서버가 켜져 있고 RCON이 닿으면 스크립트는:

1. `save-off` — 자동 저장을 멈춰 복사 중 청크가 쓰이지 않게.
2. `save-all flush` — 전부 디스크로 플러시.
3. 월드 폴더 아카이브.
4. `save-on` — 자동 저장 재개.

서버가 꺼져 있으면 폴더를 바로 아카이브합니다.

## 백업 실행

```bash
./scripts/backup.sh
```

디스코드에서는: `/backup`(로딩 애니메이션 후 결과 표시).

## 회전

최신 `BACKUP_KEEP`개(기본 **10**)만 유지하고 오래된 것은 삭제합니다. `.env`에서
조정:

```dotenv
MC_BACKUP_DIR=/home/pi/raspi-mc-server/backups
BACKUP_KEEP=10
```

32GB SD카드에서는 총 용량을 주시하세요 — 성숙한 월드는 스냅샷당 수백 MB가 될 수
있습니다. USB SSD에 백업하거나 아카이브를 기기 밖으로 복사하는 것을 고려하세요.

## cron으로 예약

매일 05:00:

```bash
crontab -e
```

```cron
0 5 * * *  /home/pi/raspi-mc-server/scripts/backup.sh >> /home/pi/mc-backup.log 2>&1
```

## 기기 밖 복사 (권장)

SD카드는 고장 납니다. 주기적으로 아카이브를 다른 곳으로 복사하세요. 예: `rclone`로
클라우드, 또는 `rsync`로 다른 머신에:

```cron
30 5 * * *  rsync -a /home/pi/raspi-mc-server/backups/ backupuser@nas:/backups/mc/
```

## 복원

```bash
sudo systemctl stop minecraft.service
./scripts/restore.sh                       # 최신 백업
# 또는: ./scripts/restore.sh backups/world_20260709_050000.tar.gz
sudo systemctl start minecraft.service
```

`restore.sh`는 서버가 켜져 있으면 실행을 거부하고, 압축을 풀기 전에 현재 월드를
`world.bak_<타임스탬프>`로 옮겨 둡니다 — 복원을 되돌릴 수 있습니다.
