"""Offline checks for the global slash-command error handler.

An unhandled command exception used to leave Discord's generic "did not
respond" and no traceback anywhere. The handler must log the failure and
still answer the user, without double-messaging denied checks.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from discord import app_commands

from bot.main import onAppCommandError


def _fakeInteraction(responded: bool = False):
    interaction = MagicMock(name="interaction")
    interaction.response.is_done.return_value = responded
    interaction.response.send_message = AsyncMock(name="send_message")
    interaction.followup.send = AsyncMock(name="followup_send")
    interaction.command.qualified_name = "admin"
    return interaction


class AppCommandErrorTests(unittest.TestCase):
    def _run(self, coro):
        return asyncio.run(coro)

    def testCheckFailureStaysSilent(self):
        """interaction_check already answered, so the handler must not."""
        interaction = _fakeInteraction()
        self._run(onAppCommandError(interaction, app_commands.CheckFailure()))
        interaction.response.send_message.assert_not_called()
        interaction.followup.send.assert_not_called()

    def testUnhandledErrorAnswersBeforeFirstResponse(self):
        interaction = _fakeInteraction(responded=False)
        error = app_commands.CommandInvokeError(
            MagicMock(), RuntimeError("boom")
        )
        self._run(onAppCommandError(interaction, error))
        interaction.response.send_message.assert_awaited_once()
        message = interaction.response.send_message.await_args.args[0]
        self.assertTrue(message.startswith("❌"))
        self.assertTrue(
            interaction.response.send_message.await_args.kwargs["ephemeral"]
        )

    def testUnhandledErrorUsesFollowupAfterResponse(self):
        interaction = _fakeInteraction(responded=True)
        error = app_commands.CommandInvokeError(
            MagicMock(), RuntimeError("boom")
        )
        self._run(onAppCommandError(interaction, error))
        interaction.followup.send.assert_awaited_once()
        interaction.response.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
