"""Regression checks for the button-first Discord account experience."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PanelUxTests(unittest.TestCase):
    """Keep removed request controls from returning to the published panels."""

    def testFriendPanelsExposeNoRequestOrApprovalCallbacks(self):
        """Friends never submit a request and admins never process a queue."""
        source = (ROOT / "bot" / "friend_panel.py").read_text(encoding="utf-8")
        friendCog = (ROOT / "bot" / "cogs" / "friend.py").read_text(
            encoding="utf-8"
        )

        for removedName in (
            "LinkNameModal",
            "LinkEditionView",
            "LinkAdminView",
            "panelRequestLink",
            "panelApproveLink",
            "panelRevokeLink",
        ):
            self.assertNotIn(removedName, source + friendCog)


if __name__ == "__main__":
    unittest.main()
