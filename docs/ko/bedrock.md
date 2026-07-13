# 자바와 베드락이 한 월드에서 같이 접속하기

이 프로젝트는 **Paper 자바 서버와 월드 하나를 그대로 유지**하면서 Geyser가
베드락 통신을 변환하고 Floodgate가 베드락 사용자를 인증하는 방식을 지원합니다.
자바 PC, 아이폰·아이패드, 안드로이드, Minecraft for Windows 사용자가 같은 월드에서
함께 플레이할 수 있습니다. 친구 기기에는 모드·플러그인·보조 앱을 설치하지 않습니다.

## 최초 실행 메뉴가 하는 일

Pi 프로비저닝과 `.env` 비밀값 설정을 끝낸 뒤 프로젝트 진입점을 실행합니다.

```bash
cd ~/raspi-mc-server
.venv/bin/python -m bot.main
```

표시 언어를 고르고 `Java + 모바일/Windows 베드락`을 선택하면 다음을 처리합니다.

1. 비밀값이 아닌 선택을 `MC_STATE_DIR/app-settings.json`에 저장
2. 없을 때만 공식 최신 Geyser-Spigot·Floodgate-Spigot jar 다운로드
3. 게시된 SHA-256과 대조한 뒤 설치
4. Geyser를 Floodgate 인증과 선택한 UDP 포트(기본 `19132`)로 설정
5. 설정에 필요할 때만 Paper 시작·재시작
6. Discord 봇과 모든 cog 시작

평소 실행 때는 플러그인 업데이트를 조회하지 않고, 이미 정상 설정된 서버를 재시작하지
않습니다. Pi의 CPU·저장장치·부팅 네트워크 부하를 줄이기 위한 동작입니다. 메뉴를 다시
열려면 봇 서비스를 멈춘 뒤 터미널에서 실행합니다.

```bash
sudo systemctl stop mc-discord-bot.service
.venv/bin/python -m bot.main --setup
```

Java 전용을 선택하면 크로스플레이 jar 두 개를 `.disabled`로 바꾸고 Paper를 한 번
재시작합니다. 나중에 크로스플레이를 선택하면 다시 다운로드하지 않고 jar를 복원합니다.
새 모드를 확인한 뒤 Ctrl+C로 포그라운드 프로세스를 끝내고 봇 서비스를 재시작하세요.

## 친구 설정: 한 번 저장하고 다음부터 딸깍

집 밖 친구도 접속한다면 서버장은 게임 포트 두 개를 열어야 합니다.

- 자바: `25565/TCP`
- 베드락: `19132/UDP`(메뉴에서 바꿨다면 그 포트)

자바 친구는 멀티플레이에서 서버 주소를 한 번 추가하면 됩니다. 아이폰·아이패드,
안드로이드 또는 Minecraft for Windows 친구는 처음 한 번만 다음처럼 합니다.

1. **플레이 → 서버 → 서버 추가**를 엽니다.
2. 서버장이 준 주소와 베드락 포트 `19132`를 입력합니다.
3. 저장하고 평소 Microsoft/Xbox 계정으로 접속합니다.

그다음부터는 저장된 서버를 탭하면 됩니다. 친구 기기에서 Geyser/Floodgate를 설정할
일은 없습니다. Xbox·PlayStation·Switch도 베드락이지만 사용자 지정 서버 UI가
제한되어 있어 이번 원탭 지원 범위에는 포함하지 않습니다.

## Discord 연동과 입장 승인

친구는 `/link request`에서 정확한 자바 닉네임 또는 Xbox 게이머태그를 입력하고
에디션을 선택합니다. 서버장이 `/link approve`를 실행하면 올바른 Paper/Floodgate
화이트리스트 명령도 함께 실행되므로 별도 화이트리스트 작업이 필요 없습니다.
Floodgate는 같은 이름의 자바 계정과 충돌하지 않도록 서버 내부 이름 앞에 `.`을
붙이지만, 친구는 평소 게이머태그만 입력합니다.

## 네트워크 주의사항

일반 Cloudflare Tunnel/HTTP 프록시는 베드락 UDP 게임 포트를 운반하지 않습니다.
친구 설정을 최소화하려면 공유기에서 `25565/TCP`와 `19132/UDP`를 포워딩하세요.
VPN은 공개 포트를 피할 수 있지만 친구마다 설치·가입이 필요합니다. RCON `25575`는
절대 외부에 열지 마세요.

## 네이티브 베드락 서버는 별도 설계

네이티브 베드락 서버를 따로 실행하면 서버와 월드가 분리되고 이 Paper/RCON 봇 설계를
그대로 쓰지 못합니다. 혼합 기기 지원은 Geyser + Floodgate 방식이 이 저장소의 지원
경로입니다. 자바·베드락 차이로 일부 번역 한계는 있지만 모든 플레이어는 같은 Paper
월드에 있습니다.

공식 자료: [Geyser 설정](https://geysermc.org/wiki/geyser/setup/),
[Floodgate 설정](https://geysermc.org/wiki/floodgate/setup/paper-spigot/),
[현재 한계](https://geysermc.org/wiki/geyser/current-limitations/).
