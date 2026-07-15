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

    def testAdminDashboardUsesPlainActionLabels(self):
        """The busiest panel names outcomes instead of implementation concepts."""
        source = (ROOT / "bot" / "control_panel.py").read_text(encoding="utf-8")

        for label in (
            "접속자 관리",
            "서버 제어",
            "성능 상세",
            "렉 원인",
            "긴급 복구",
            "친구 계정",
            "관리 도움말",
        ):
            self.assertIn(f'label="{label}"', source)

    def testAdminHelpExplainsAccountsAndUploads(self):
        """Private help covers the two workflows that otherwise require discovery."""
        source = (ROOT / "bot" / "cogs" / "admin.py").read_text(encoding="utf-8")

        self.assertIn("관리자 전용 도움말", source)
        self.assertIn("한 Discord 사용자에게 여러 계정", source)
        self.assertIn("/업로드", source)

    def testAccountSelectorsNameDeviceTypes(self):
        """Users can distinguish PC and mobile profiles before acting."""
        source = (ROOT / "bot" / "friend_panel.py").read_text(encoding="utf-8")

        self.assertIn("Java (PC)", source)
        self.assertIn("Bedrock (모바일/콘솔)", source)
        self.assertIn("사용할 Minecraft 계정 선택", source)


if __name__ == "__main__":
    unittest.main()
