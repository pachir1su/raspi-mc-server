# HDD 자동 백업·복구·맵 관리

현재 월드와 큰 파일은 500GB 외장 HDD의 `/mnt/minecraft`에 저장합니다. 봇은 이
경로가 실제 마운트포인트인지 확인하므로, HDD가 빠졌을 때 microSD에 백업을 잘못
쌓지 않습니다.

## 저장 구조

```text
/mnt/minecraft/
├── live/          # PaperMC와 현재 월드
├── backups/       # .tar.gz 백업과 SHA-256
├── worlds/        # 검증 완료된 업로드 맵
├── uploads/       # 다운로드용 임시 파일
├── staging/       # 안전한 압축 해제·복구
└── quarantine/    # 격리용 예약 공간
```

## 자동 백업 정책

봇이 1분마다 설정을 확인하고 기본 **30분 간격**으로 백업합니다. 서버 실행 중에는
`save-off`, `save-all flush`, 백업, `save-on` 순서로 일관된 스냅샷을 만듭니다.

- 최근 48시간: 모든 백업 유지
- 이후 30일: 하루 최신 백업 1개 유지
- HDD 사용률 80% 이상 또는 여유 30GB 미만이면 새 백업 중단
- `/backup configure` 변경값은 `data/backup-settings.json`에 영구 저장
- 최소 허용 주기는 10분

`/backup settings`에서 현재 정책과 HDD 용량을 확인하고 다음처럼 변경합니다.

```text
/backup configure interval_minutes:30 retention_hours:48 daily_retention_days:30
/backup configure max_usage_percent:80 min_free_gb:30
/backup enabled enabled:false
```

## 백업과 복구

```text
/backup create
/backup list
/backup download name:<파일명>
/backup restore name:<파일명> confirm:RESTORE
/backup delete name:<파일명> confirm:DELETE
```

복구는 현재 월드 비상 백업을 먼저 만들고, 서버 정지에 성공한 뒤에만 월드를
교체합니다. 디렉터리 교체가 실패하면 이전 월드를 되돌립니다. 복구가 끝나면 서버를
다시 시작합니다.

디스코드 서버의 실제 첨부 한도보다 큰 백업은 `/backup download`로 보낼 수
없습니다. 이때는 SSH/SFTP로 `/mnt/minecraft/backups`에서 받으세요.

## 맵 업로드와 전환

```text
/world upload name:<보관이름> file:<zip/tar.gz/tgz>
/world list
/world activate name:<보관이름> confirm:ACTIVATE
/world download name:<보관이름>
/world delete name:<보관이름> confirm:DELETE
```

업로드 파일은 Java Edition 월드의 `level.dat`를 정확히 하나 포함해야 합니다.
봇은 경로 탈출, 링크, 장치 파일, 100GiB 초과 압축 폭탄과 과도한 파일 수를
거부합니다. 맵 전환 전에도 현재 월드를 자동 백업합니다.

## HDD 장애와 실제 백업

현재 월드와 백업이 같은 HDD에 있으므로 실수나 월드 손상은 복구할 수 있지만 HDD
자체 고장에는 대비할 수 없습니다. 중요한 백업은 주기적으로 다른 PC, NAS 또는
클라우드에도 복사하세요.
