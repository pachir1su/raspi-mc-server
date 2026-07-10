"""Minimal async RCON client for the Minecraft (Source) RCON protocol.

Implemented directly on asyncio streams to avoid an extra dependency. The
protocol is small: length-prefixed little-endian packets carrying a request
id, a type, and an ASCII payload.

Packet types:
  3 = login (auth)      2 = command      0 = response value

Usage:
    async with Rcon(host, port, password) as r:
        out = await r.command("list")
"""

import asyncio
import struct

TYPE_AUTH = 3
TYPE_COMMAND = 2
TYPE_RESPONSE = 0


class RconError(Exception):
    """RCON connection or authentication failure."""


class Rcon:
    def __init__(self, host: str, port: int, password: str, timeout: float = 8.0):
        self._host = host
        self._port = port
        self._password = password
        self._timeout = timeout
        self._reader = None
        self._writer = None
        self._id = 0

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
        except (OSError, asyncio.TimeoutError) as e:
            raise RconError(f"cannot reach RCON at {self._host}:{self._port}: {e}")
        # Authenticate. A response id of -1 means the password was rejected.
        rid = await self._send(TYPE_AUTH, self._password)
        if rid == -1:
            await self.close()
            raise RconError("RCON authentication failed (wrong password)")

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
            raise RconError("not connected")
        await self._send(TYPE_COMMAND, cmd)
        return self._last_body

    # --- wire protocol -------------------------------------------------
    async def _send(self, ptype: int, payload: str) -> int:
        self._id += 1
        req_id = self._id
        body = payload.encode("utf-8") + b"\x00\x00"
        packet = struct.pack("<ii", req_id, ptype) + body
        packet = struct.pack("<i", len(packet)) + packet
        self._writer.write(packet)
        await self._writer.drain()
        resp_id, self._last_body = await self._read()
        return resp_id

    async def _read(self):
        raw_len = await asyncio.wait_for(self._reader.readexactly(4), self._timeout)
        (length,) = struct.unpack("<i", raw_len)
        data = await asyncio.wait_for(self._reader.readexactly(length), self._timeout)
        resp_id, _ptype = struct.unpack("<ii", data[:8])
        body = data[8:-2].decode("utf-8", errors="replace")  # strip two null bytes
        return resp_id, body
