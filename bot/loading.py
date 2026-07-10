"""A small loading animation for slow slash commands.

Discord forces its own "Bot is thinking…" text when you ``defer``, and you
cannot replace it. So instead we send our OWN embed as the first response
and edit it on a timer with a progress bar that eases toward a cap (never
reaching 100% — the real result replaces it when the work finishes). This
gives a lively "working…" feel for actions like a backup or a restart.

The bar eases (fast then slow) so an action of unknown duration still looks
like it is progressing. Frame edits are spaced comfortably inside Discord's
edit rate limit; failed edits (message deleted, rate limited) are ignored —
the animation is cosmetic and must never block the real work.
"""

import asyncio

import discord

from bot import BRAND_BLUE

_BAR_WIDTH = 14
_FILLED = "█"
_EMPTY = "░"
_FRAME_INTERVAL = 1.5   # seconds between edits (well within the rate limit)
_PCT_CAP = 96           # never show 100% before the work is actually done
_EASE = 0.74            # each frame closes this fraction of the remaining gap


def _percent(step: int) -> int:
    remaining = (1 - _EASE) ** max(0, step)
    return int(round(_PCT_CAP * (1 - remaining)))


def _bar(pct: int) -> str:
    pct = max(0, min(100, pct))
    count = round(pct / 100 * _BAR_WIDTH)
    return _FILLED * count + _EMPTY * (_BAR_WIDTH - count)


def _embed(label: str, step: int) -> discord.Embed:
    pct = _percent(step)
    e = discord.Embed(
        title=f"⏳ {label}",
        description=f"```\n{_bar(pct)} {pct:>3d}%\n```",
        color=BRAND_BLUE,
    )
    return e


async def animate_while(interaction: discord.Interaction, work, label: str):
    """Run coroutine ``work`` while showing the loading animation.

    Sends the first frame as the initial response, edits frames until the
    work completes, then returns whatever ``work`` returned. The caller is
    responsible for replacing the loading embed with the final result via
    ``interaction.edit_original_response(...)``.
    """
    await interaction.response.send_message(embed=_embed(label, 0))

    task = asyncio.ensure_future(work)
    step = 1
    while not task.done():
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=_FRAME_INTERVAL)
        except asyncio.TimeoutError:
            try:
                await interaction.edit_original_response(embed=_embed(label, step))
            except discord.HTTPException:
                pass  # cosmetic only
            step += 1
    return await task
