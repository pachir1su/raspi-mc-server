# 원격 접속 — RCON, SSH, Cloudflare Tunnel

서버에 접근·관리하는 세 가지 방법을, 가장 로컬한 것부터 가장 원격인 것 순으로
소개합니다. LAN 밖 **플레이어**가 접속하려면 아래 노출 옵션(또는 포트포워딩) 중
하나가 필요합니다.

## 1. SSH + RCON (기본)

가장 단순한 원격 콘솔: 파이에 SSH로 들어가 `mcrcon` 사용.

```bash
ssh pi@파이-LAN-IP
cd raspi-mc-server
# .env 에 RCON_* 가 있음; source 하거나 플래그로 직접 전달
mcrcon -H 127.0.0.1 -P 25575 -p "$RCON_PASSWORD" "list"
mcrcon -H 127.0.0.1 -P 25575 -p "$RCON_PASSWORD" "gamemode creative 내닉네임"
```

RCON은 op 레벨 4로 실행되므로 완전한 관리/치트 콘솔입니다. RCON은 localhost에
묶어 두고 — **25575 포트를 인터넷에 포워딩하지 마세요**.

## 2. 디스코드 봇 (주력)

일상적으로, 특히 폰에서 가장 편합니다. [discord-bot.md](discord-bot.md) 참고.
봇은 localhost의 RCON에 접속하므로 노출되는 포트가 없습니다.

## 3. Cloudflare Tunnel (선택, 포트포워딩 불필요)

[Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
(`cloudflared`)은 아웃바운드 전용 연결을 제공합니다 — 공유기 포트포워딩도, 집
공인 IP 노출도 없습니다. 흔한 두 용도:

### a) 관리용 웹/SSH를 터널로

SSH나 작은 관리 웹 페이지(추가한다면)를 터널로 노출하고 **Cloudflare Access**
(이메일/SSO)로 보호해 나만 접근하게 합니다.

```bash
# 파이에서
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o cloudflared
sudo install cloudflared /usr/local/bin/
cloudflared tunnel login
cloudflared tunnel create raspi-mc
# 호스트명을 로컬 서비스로 라우팅(예: 22번 SSH)
cloudflared tunnel route dns raspi-mc mc-admin.example.com
```

`~/.cloudflared/config.yml`에 터널 설정을 넣고 서비스로 실행:

```yaml
tunnel: raspi-mc
credentials-file: /home/pi/.cloudflared/<TUNNEL_ID>.json
ingress:
  - hostname: mc-admin.example.com
    service: ssh://localhost:22
  - service: http_status:404
```

```bash
sudo cloudflared service install
```

접속: `cloudflared access ssh --hostname mc-admin.example.com`.

### b) 플레이어 트래픽

마인크래프트 자바 프로토콜은 HTTP가 아니라 순수 TCP라, 무료 Cloudflare HTTP
프록시로는 게임 포트를 **실어 나르지 못합니다**. 플레이어용 옵션:

- **Cloudflare Tunnel TCP** — 각 플레이어가 `cloudflared access tcp`를 실행해야
  함(친구에겐 번거로움).
- **포트포워딩** — 공유기에서 `25565/tcp`를 파이로(플레이어에겐 가장 간단; 게임
  포트만 노출).
- **VPN**(Tailscale/WireGuard) — 친구를 내 tailnet에 추가하고 파이의 VPN IP로
  접속. 공개 노출이 전혀 없음. 3~4명 친구 서버엔 대개 가장 좋은 선택입니다.

> 추천: 플레이어는 **Tailscale**(또는 `25565`만 포트포워딩), 관리는
> **Cloudflare Access + 디스코드 봇**.

## 보안 요약

- 플레이어에게는 게임 포트(25565)만 노출하거나 VPN으로 비공개 유지.
- RCON(25575)·SSH는 직접 노출 금지; 터널/VPN으로 감싸고 Access나 키로 보호.
- RCON은 강력·고유한 비밀번호를 쓰고 절대 커밋하지 않기.
