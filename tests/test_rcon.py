"""Regression tests for the async RCON client (이슈 A).

가짜 RCON 서버를 asyncio로 띄워 정상 응답 / 인증 실패 / 타임아웃 세 시나리오를
검증합니다. 실제 배포에서 "TCP는 되는데 항상 unreachable"로 오판하던 문제를
막기 위한 것입니다.
"""

import asyncio
import os
import struct
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from bot.rcon import (
    Rcon,
    RconAuthError,
    RconConnectionError,
    RconTimeout,
    _main,
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
                if self.behaviour == "multipacket" and body:
                    # 4KB를 넘는 응답처럼 한 명령 응답을 두 패킷으로 쪼개 보냅니다
                    # (같은 req id). 빈 센티넬 패킷은 아래 일반 경로로 되돌려 줍니다.
                    writer.write(_pack(cmd_id, TYPE_RESPONSE, "PART1-" * 800))
                    writer.write(_pack(cmd_id, TYPE_RESPONSE, "-PART2"))
                    await writer.drain()
                    continue
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

    async def testConcatenatesMultiPacketResponse(self):
        # #90: 인벤토리처럼 4KB를 넘어 여러 패킷으로 쪼개진 응답을 끝까지
        # 이어 붙여야 합니다. 한 패킷만 읽으면 뒷부분이 잘려 파싱이 실패합니다.
        async with FakeRconServer("multipacket") as server:
            async with Rcon("127.0.0.1", server.port, "secret", timeout=5) as client:
                out = await client.command("data get entity @p Inventory")
        self.assertTrue(out.startswith("PART1-"))
        self.assertTrue(out.endswith("-PART2"))
        self.assertEqual(len("PART1-") * 800 + len("-PART2"), len(out))


class RconCliTests(unittest.IsolatedAsyncioTestCase):
    def testCliLoadsDotenvBeforeReadingPassword(self):
        class FakeRcon:
            def __init__(self, host, port, password):
                self.password = password

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return None

            async def command(self, command):
                return f"{self.password}:{command}"

        def loadEnvironment():
            os.environ["RCON_PASSWORD"] = "from-dotenv"

        with patch.dict(os.environ, {}, clear=True), patch(
            "dotenv.load_dotenv", side_effect=loadEnvironment
        ) as loadDotenv, patch("bot.rcon.Rcon", FakeRcon), redirect_stdout(
            StringIO()
        ) as output:
            self.assertEqual(0, _main(["list"]))

        loadDotenv.assert_called_once_with()
        self.assertEqual("from-dotenv:list", output.getvalue().strip())

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
        # OS별 예약 포트 동작에 의존하지 않고 연결 거부를 직접 재현합니다.
        with patch("bot.rcon.asyncio.open_connection", side_effect=OSError("refused")):
            with self.assertRaises(RconConnectionError):
                async with Rcon("127.0.0.1", 25575, "secret", timeout=1):
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
