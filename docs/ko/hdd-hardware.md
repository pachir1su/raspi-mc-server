# HDD 규격·케이스·전원 선택

이 서버는 월드와 백업을 USB HDD의 `/mnt/minecraft`에 둡니다. HDD가 순간적으로
끊기면 렉으로 끝나지 않고 월드 쓰기 실패나 파일시스템 손상으로 이어질 수 있으므로,
용량보다 **규격과 전원 안정성**을 먼저 확인합니다.

## `100 × 700 mm` 측정값 해석

`100 × 700 mm`가 아니라 **약 100 × 70 mm**를 뜻했다면 일반적인 **2.5인치 SATA
HDD** 크기입니다. 실제 2.5인치 제품 예시는 너비 69.85mm, 길이 100.35mm입니다.
700mm는 70cm이므로 노트북용 HDD가 아닙니다. 자로 다시 아래 세 방향을 잽니다.

| 잴 곳 | 2.5인치 HDD의 흔한 값 | 의미 |
|---|---:|---|
| 길이 | 약 100mm | 사용자가 말한 `100`과 일치 |
| 너비 | 약 70mm | `700`은 `70.0` 오타일 가능성이 큼 |
| 두께 | 7mm 또는 9.5mm | 케이스 호환을 결정하는 값 |

“7인치/10인치”가 아니라 보통 **두께 7mm/9.5mm(약 10mm)**를 말합니다. 정확한
모델 번호가 있으면 제조사 데이터시트가 최종 기준입니다. [Seagate 2.5인치
데이터시트](https://www.seagate.com/www-content/product-content/barracuda-fam/barracuda-new/files/barracuda-2-5-ds1907-1-1609us.pdf)는
7mm 제품의 69.85 × 100.35mm 규격과 모델별 시작 전류를 보여 줍니다.

## 2.5인치 7mm와 9.5mm

| 항목 | 7mm | 9.5mm(흔히 “10mm”) |
|---|---|---|
| 용도 | 얇은 노트북 HDD/SSD | 구형·일반 노트북 HDD |
| 9.5mm 대응 케이스 | 들어가지만 흔들릴 수 있음 | 맞음 |
| 7mm 전용 케이스 | 맞음 | 뚜껑이 닫히지 않음 |
| 해결 | 동봉 스페이서/패드로 고정 | 9.5mm 이상 지원 케이스 선택 |

구매 설명에 **“2.5-inch SATA, 7/9.5mm, USB 3.x, UASP”**가 모두 있는 케이스를
고릅니다. M.2 SATA, M.2 NVMe, 3.5인치 IDE 케이스는 모양과 전기 규격이 다릅니다.
HDD의 넓은 15핀 전원부와 좁은 7핀 데이터부가 붙은 **22핀 SATA** 커넥터인지
사진으로 확인합니다.

케이스 선택 권장 순서:

1. 2.5인치 **SATA**와 실제 두께 지원.
2. USB 3.0 이상과 UASP 지원.
3. Raspberry Pi에서 SMART 전달을 지원하는 칩셋.
4. 짧고 굵은 USB 케이블, 헐겁지 않은 단자.
5. 24시간 사용 시 열이 빠지는 금속 또는 통풍 구조.
6. 전원 불안정 시 별도 DC 입력이 있는 케이스 또는 검증된 전원형 USB 허브.

## 3.5인치 HDD와 구별

3.5인치 HDD는 대략 **147 × 101.6 × 20~26.1mm**로, 2.5인치보다 훨씬 넓고
두껍습니다. 5V뿐 아니라 **12V도 필요**하므로 Raspberry Pi USB만으로는 돌릴 수
없습니다. 반드시 자체 어댑터가 있는 3.5인치 USB 케이스/도크를 사용합니다.
[Seagate 3.5인치 데이터시트](https://www.seagate.com/www-content/product-content/pipeline-fam/pipeline-hd/video-3-5-hdd/en-us/docs/video-3-5-hdd-data-sheet-ds1783-2-1306us.pdf)는
101.6 × 146.99 × 최대 26.11mm, 5V/12V 입력과 모델에 따라 12V 시작 전류 2A를
명시합니다.

| 실제 장치 | 필요한 연결 |
|---|---|
| 2.5인치 SATA HDD | SATA→USB 3 케이스; 아래 전력 점검 후 USB 전원 또는 전원형 허브 |
| 3.5인치 SATA HDD | **자체 12V 어댑터가 있는** 케이스/도크 필수 |
| 완제품 외장 HDD | 원래 케이블과 원래 전원 어댑터 사용 |
| M.2 SSD | HDD 케이스가 아니라 SATA/NVMe 방식에 맞는 M.2 케이스 필요 |

## 외부 전원 없이 쓰면

Raspberry Pi 4B 권장 입력은 **5V 3A**이고 USB 포트 네 개가 주변 장치에 공급하는
전류 예산은 합계 기준으로 제한됩니다. [Raspberry Pi 하드웨어
문서](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)와
[전원 안내](https://www.raspberrypi.com/documentation/computers/getting-started.html)를
기준으로 공식 15W급 전원과 짧고 품질 좋은 USB-C 케이블을 사용합니다.

2.5인치 HDD는 평소 소비 전력이 낮아 보이더라도 플래터가 돌기 시작할 때 순간 전류가
커집니다. 예시 데이터시트의 시작 전류는 5V에서 모델별 1.0~1.2A입니다. Pi, 팬,
키보드/동글 등과 같은 전원 예산을 공유하므로 “한 번 부팅됐다”가 24시간 안정성을
보장하지 않습니다.

전력이 부족하면 다음 증상이 나타날 수 있습니다.

- HDD가 회전 시작을 반복하거나 딸깍거림.
- `/dev/sda`가 사라졌다 다시 생기고 USB reset/UAS 오류가 기록됨.
- `/mnt/minecraft` I/O 오류, Paper 멈춤, 청크 저장 실패.
- Pi 저전압·스로틀링으로 TPS 저하와 끊김.
- 부팅 실패, 갑작스러운 재부팅, ext4 또는 월드 손상.

**무화면 24시간 서버 권장안은 전원형 USB 3 허브 또는 자체 전원 케이스**입니다.
전원형 허브는 데이터 케이블로 Pi에 연결하고 허브 제조사가 지정한 어댑터를 씁니다.
[Raspberry Pi USB Hub 문서](https://www.raspberrypi.com/documentation/accessories/usb.html)는
자체 전원 사용 시 허브가 최대 5V 3A를 공급하는 구성을 설명합니다.

다음은 피합니다.

- 규격 불명 Y 케이블로 Pi의 USB 포트 두 개에서 억지로 전류를 합치는 것.
- 역급전 방지 설계가 불명확한 허브.
- 3.5인치 HDD를 USB 전원만으로 시도하는 것.
- 전원이 켜진 상태에서 HDD 케이블을 뽑는 것.

## 연결 후 무화면 점검

```bash
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,FSTYPE,MOUNTPOINTS
lsusb -t
findmnt /mnt/minecraft
vcgencmd get_throttled
sudo dmesg -T | grep -Ei 'under-voltage|voltage|usb|uas|reset|I/O error'
```

`get_throttled=0x0`이 정상입니다. 부하를 걸어야 드러나는 문제도 있으므로 서버와
백업을 한 번 실행한 뒤 다시 확인합니다. `reset SuperSpeed USB device`, `uas`,
`I/O error`, 저전압이 반복되면 파일시스템을 고치기 전에 케이블과 전원을 해결합니다.

SMART 확인은 브리지 지원 여부에 따라 달라집니다.

```bash
sudo apt install -y smartmontools
sudo smartctl --scan-open
sudo smartctl -a /dev/sda
# SAT 브리지가 필요하다고 나오면
sudo smartctl -a -d sat /dev/sda
```

## 설치와 운용 체크리스트

- [ ] 실측이 약 `100 × 70 × 7/9.5mm`인지 확인.
- [ ] 2.5인치 SATA와 두께에 맞는 USB 3 케이스 사용.
- [ ] 3.5인치라면 12V 자체 전원 어댑터 사용.
- [ ] Pi는 안정적인 5V 3A 전원 사용.
- [ ] HDD를 파란색 USB 3 포트에 연결.
- [ ] 케이블 장력·진동·열이 없도록 고정하고 통풍 확보.
- [ ] `get_throttled=0x0`, USB reset/I/O 오류 없음 확인.
- [ ] `/mnt/minecraft`가 없으면 봇/Paper를 억지로 시작하지 않음.
- [ ] 같은 HDD의 백업 외에 다른 PC/디스크에도 중요 백업 보관.

파티션과 ext4 마운트 절차는 [헤드리스 전체 설치](headless-setup.md#7-500gb-hdd-준비),
장애 대응은 [운영 런북](operator-runbook.md#hdd가-사라졌을-때)을 따릅니다.
