"""Regression tests for the async RCON client (이슈 A).

가짜 RCON 서버를 asyncio로 띄워 정상 응답 / 인증 실패 / 타임아웃 세 시나리오를
검증합니다. 실제 배포에서 "TCP는 되는데 항상 unreachable"로 오판하던 문제를
막기 위한 것입니다.
"""

import asyncio
import struct
import unittest

from bot.rcon import (
    Rcon,
    RconAuthError,
    RconConnectionError,
    RconTimeout,
)

TYPE_AUTH = 3
TYPE_AUTH_RESPONSE = 2
TYPE_RESPONSE = 0


def _pack(req_id: int, ptype: int, body: str) -> bytes:
    payload = struct.pack("<ii", req_id, ptype) + body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload


async def _readPacket(reader: asyncio.StreamReader):
    raw_len = await reader.readexactly(4)
    (length,) = struct.unpack("<i", raw_len)
    data = await reader.readexactly(length)
    req_id, ptype = struct.unpack("<ii", data[:8])
    body = data[8:-2].decode("utf-8", errors="replace")
    return req_id, ptype, body


class FakeRconServer:
    """A minimal Source-RCON server with selectable behaviour."""

    def __init__(self, behaviour: str = "ok"):
        self.behaviour = behaviour
        self._server = None
        self.port = None

    async def __aenter__(self):
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc):
        self._server.close()
        await self._server.wait_closed()

    async def _handle(self, reader, writer):
        try:
            req_id, ptype, _password = await _readPacket(reader)
            if ptype != TYPE_AUTH:
                writer.close()
                return
            if self.behaviour == "timeout":
                # TCP는 열렸지만 응답을 주지 않아 클라이언트가 포기하게 만듭니다.
                await asyncio.sleep(30)
                return
            if self.behaviour == "badpass":
                writer.write(_pack(-1, TYPE_AUTH_RESPONSE, ""))
                await writer.drain()
                writer.close()
                return
            # ok: 일부 서버처럼 인증 응답 앞에 빈 RESPONSE_VALUE를 먼저 보냅니다.
            writer.write(_pack(req_id, TYPE_RESPONSE, ""))
            writer.write(_pack(req_id, TYPE_AUTH_RESPONSE, ""))
            await writer.drain()
            while True:
                cmd_id, cmd_type, body = await _readPacket(reader)
                reply = "There are 0 of a max of 20 players online:" if body == "list" else body
                writer.write(_pack(cmd_id, TYPE_RESPONSE, reply))
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            try:
                writer.close()
            except OSError:
                pass


class RconClientTests(unittest.IsolatedAsyncioTestCase):
    async def testSuccessfulCommandDespiteLeadingEmptyPacket(self):
        async with FakeRconServer("ok") as server:
            async with Rcon("127.0.0.1", server.port, "secret", timeout=5) as client:
                out = await client.command("list")
            self.assertIn("players online", out)

    async def testWrongPasswordRaisesAuthError(self):
        async with FakeRconServer("badpass") as server:
            with self.assertRaises(RconAuthError):
                async with Rcon("127.0.0.1", server.port, "wrong", timeout=5):
                    pass

    async def testUnresponsiveServerRaisesTimeout(self):
        async with FakeRconServer("timeout") as server:
            with self.assertRaises(RconTimeout):
                async with Rcon("127.0.0.1", server.port, "secret", timeout=0.3):
                    pass

    async def testClosedPortRaisesConnectionError(self):
        # 아무도 듣고 있지 않은 포트 → 연결 자체가 실패해야 합니다.
        with self.assertRaises(RconConnectionError):
            async with Rcon("127.0.0.1", 1, "secret", timeout=1):
                pass

    async def testLongHexPasswordAuthenticates(self):
        # 64자 hex 비밀번호도 정상 처리되는지 확인(실배포 재현 케이스).
        password = "a1b2c3d4" * 8
        async with FakeRconServer("ok") as server:
            async with Rcon("127.0.0.1", server.port, password, timeout=5) as client:
                out = await client.command("list")
            self.assertIn("players online", out)


if __name__ == "__main__":
    unittest.main()
