"""Raspberry Pi Java 설치 스크립트의 회귀 테스트입니다."""

from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = (REPO_DIR / "deploy" / "setup_raspberrypi.sh").read_text(
    encoding="utf-8"
)
INSTALL_SCRIPT = (REPO_DIR / "scripts" / "install_server.sh").read_text(
    encoding="utf-8"
)


def testSetupUsesCorretto25WithoutLegacyHeadlessPackage():
    """설정 스크립트가 Corretto 25와 Paper 의존 패키지만 설치하는지 확인합니다."""
    legacyPackage = "openjdk" + "-21"

    assert legacyPackage not in SETUP_SCRIPT
    assert "https://apt.corretto.aws/corretto.key" in SETUP_SCRIPT
    assert "https://apt.corretto.aws stable main" in SETUP_SCRIPT
    assert "java-25-amazon-corretto-jdk" in SETUP_SCRIPT
    for dependency in ("libxi6", "libxtst6", "libxrender1"):
        assert dependency in SETUP_SCRIPT


def testSetupSkipsInstallAndVerifiesJava25():
    """Java 25 이상 건너뛰기와 설치 후 하한 검사가 모두 있는지 확인합니다."""
    assert '[ "$JAVA_MAJOR" -ge 25 ]' in SETUP_SCRIPT
    assert '[ "$JAVA_MAJOR" -lt 25 ]' in SETUP_SCRIPT
    assert "Java 25 이상을 사용할 수 없습니다." in SETUP_SCRIPT
    assert "exit 1" in SETUP_SCRIPT


def testInstallerKeepsFillMinimumJavaCheckWithoutAptFallback():
    """Fill v3 최소 Java 조회는 유지하고 직접 apt 설치는 하지 않는지 확인합니다."""
    assert "https://fill.papermc.io/v3/projects/paper" in INSTALL_SCRIPT
    assert ".version.java.version.minimum" in INSTALL_SCRIPT
    assert "./deploy/setup_raspberrypi.sh" in INSTALL_SCRIPT
    assert "apt-get install" not in INSTALL_SCRIPT
    assert "openjdk" + "-21" not in INSTALL_SCRIPT
