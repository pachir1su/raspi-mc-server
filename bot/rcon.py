"""Minimal async RCON client for the Minecraft (Source) RCON protocol.

Implemented directly on asyncio streams to avoid an extra dependency. The
protocol is small: length-prefixed little-endian packets carrying a request
id, a type, and an ASCII payload.

Packet types:
  3 = login (auth)      2 = command      0 = response value

Usage:
    async with Rcon(host, port, password) as r:
        out = await r.command("list")

실패 원인을 구분하기 위해 예외를 세분화합니다(이슈 A):
  - RconConnectionError: TCP 연결 자체가 안 되는 경우(서버 정지/기동 중)
  - RconAuthError: 연결은 됐지만 비밀번호가 틀린 경우
  - RconTimeout: 연결·인증은 시도됐지만 응답이 제한 시간 안에 안 온 경우
모두 RconError를 상속하므로 기존 `except RconError`는 그대로 동작합니다.
"""

import asyncio
import os
import struct

from bot import log

TYPE_AUTH = 3
TYPE_AUTH_RESPONSE = 2
TYPE_COMMAND = 2
TYPE_RESPONSE = 0

# Pi에서 RCON 스레드가 응답을 내보내기까지 시간이 걸릴 수 있어 기본값을 넉넉히 둡니다.
DEFAULT_TIMEOUT = float(os.getenv("RCON_TIMEOUT", "10"))

_log = log.get("rcon")


class RconError(Exception):
    """RCON connection or authentication failure (base type)."""


class RconConnectionError(RconError):
    """TCP 연결을 열 수 없음 — 서버가 정지했거나 기동 중."""


class RconAuthError(RconError):
    """연결은 됐지만 RCON 비밀번호가 거부됨."""


class RconTimeout(RconError):
    """연결/인증은 시도됐지만 제한 시간 안에 응답이 오지 않음."""


class Rcon:
    def __init__(self, host: str, port: int, password: str,
                 timeout: float = DEFAULT_TIMEOUT):
        self._host = host
        self._port = port
        self._password = password
        self._timeout = timeout
        self._reader = None
        self._writer = None
        self._id = 0
        self._last_body = ""

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def connect(self):
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), self._timeout
            )
        except asyncio.TimeoutError as e:
            _log.warning("RCON connect timed out (%s:%s)", self._host, self._port)
            raise RconTimeout(
                f"RCON connect to {self._host}:{self._port} timed out"
            ) from e
        except OSError as e:
            _log.warning("RCON connect failed (%s:%s): %s", self._host, self._port, e)
            raise RconConnectionError(
                f"cannot reach RCON at {self._host}:{self._port}: {e}"
            ) from e
        try:
            await self._authenticate()
        except RconError:
            await self.close()
            raise

    async def _authenticate(self):
        """Send the login packet and confirm a real AUTH_RESPONSE accepts it.

        일부 서버는 인증 응답(type 2) 앞에 빈 RESPONSE_VALUE(type 0) 패킷을 먼저
        보냅니다. 첫 패킷만 읽으면 인증 결과를 오판할 수 있으므로 type 2 패킷을
        받을 때까지 읽습니다. 인증 실패 시 서버는 request id를 -1로 돌려줍니다.
        """
        req_id = self._next_id()
        await self._write(TYPE_AUTH, self._password)
        while True:
            resp_id, ptype, _body = await self._read()
            if ptype == TYPE_AUTH_RESPONSE:
                break
            # 인증 응답 앞의 빈 RESPONSE_VALUE는 무시하고 계속 읽습니다.
        if resp_id == -1:
            await self.close()
            _log.warning("RCON authentication rejected (wrong password)")
            raise RconAuthError("RCON authentication failed (wrong password)")
        if resp_id != req_id:
            # 정상 서버는 request id를 그대로 돌려줍니다. 다르면 프로토콜 오류.
            await self.close()
            _log.warning("unexpected RCON auth response id %s (sent %s)", resp_id, req_id)
            raise RconAuthError("unexpected RCON authentication response")

    async def close(self):
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except OSError:
                pass
            self._writer = None
            self._reader = None

    async def command(self, cmd: str) -> str:
        """Send a command and return the server's text response."""
        if self._writer is None:
            raise RconConnectionError("not connected")
        await self._write(TYPE_COMMAND, cmd)
        _resp_id, _ptype, body = await self._read()
        return body

    # --- wire protocol -------------------------------------------------
    def _next_id(self) -> int:
        self._id += 1
        return self._id

    async def _write(self, ptype: int, payload: str):
        """Frame and send a single request packet."""
        req_id = self._id if ptype == TYPE_AUTH else self._next_id()
        body = payload.encode("utf-8") + b"\x00\x00"
        packet = struct.pack("<ii", req_id, ptype) + body
        packet = struct.pack("<i", len(packet)) + packet
        try:
            self._writer.write(packet)
            await self._writer.drain()
        except OSError as e:
            raise RconConnectionError(f"RCON write failed: {e}") from e

    async def _read(self):
        """Read one framed packet, mapping timeouts and EOF to typed errors."""
        try:
            raw_len = await asyncio.wait_for(
                self._reader.readexactly(4), self._timeout
            )
            (length,) = struct.unpack("<i", raw_len)
            data = await asyncio.wait_for(
                self._reader.readexactly(length), self._timeout
            )
        except asyncio.TimeoutError as e:
            _log.warning("RCON response timed out after %.0fs", self._timeout)
            raise RconTimeout("RCON response timed out") from e
        except (asyncio.IncompleteReadError, OSError) as e:
            raise RconConnectionError("RCON connection closed early") from e
        resp_id, ptype = struct.unpack("<ii", data[:8])
        self._last_body = data[8:-2].decode("utf-8", errors="replace")  # strip two nulls
        return resp_id, ptype, self._last_body


def _main(argv=None) -> int:
    """Tiny CLI so operators can run one RCON command without the mcrcon binary.

    mcrcon는 Debian 저장소에 없어 설치가 번거로우므로(이슈 J), 내장 클라이언트를
    재사용합니다. RCON_HOST/RCON_PORT/RCON_PASSWORD는 .env(또는 환경)에서 읽습니다.

        .venv/bin/python -m bot.rcon "op YourName"
    """
    import sys

    args = sys.argv[1:] if argv is None else argv
    if not args:
        print('usage: python -m bot.rcon "<command>"', file=sys.stderr)
        return 2
    password = os.getenv("RCON_PASSWORD", "")
    if not password:
        print("RCON_PASSWORD is not set", file=sys.stderr)
        return 2
    host = os.getenv("RCON_HOST", "127.0.0.1")
    port = int(os.getenv("RCON_PORT", "25575"))
    command = " ".join(args)

    async def run() -> str:
        async with Rcon(host, port, password) as client:
            return await client.command(command)

    try:
        print(asyncio.run(run()))
        return 0
    except RconError as error:
        print(f"RCON error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
