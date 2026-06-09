"""plugins/shell_integration.py 测试 - Shell 代理自动恢复"""
from autosocks.plugins.shell_integration import install_integration, uninstall_integration


class TestInstallIntegration:
    """测试安装 Shell 集成"""

    def test_install_creates_script(self, tmp_path):
        """安装时创建脚本文件"""
        script = tmp_path / "autosocks.sh"
        install_integration(script, port=1080)
        content = script.read_text()
        assert "autosocks" in content
        assert "1080" in content

    def test_install_idempotent(self, tmp_path):
        """重复安装不报错"""
        script = tmp_path / "autosocks.sh"
        install_integration(script, port=1080)
        install_integration(script, port=1080)
        assert script.exists()


class TestUninstallIntegration:
    """测试卸载 Shell 集成"""

    def test_uninstall_removes_script(self, tmp_path):
        """卸载时删除脚本文件"""
        script = tmp_path / "autosocks.sh"
        script.write_text("test")
        uninstall_integration(script)
        assert not script.exists()

    def test_uninstall_nonexistent(self, tmp_path):
        """卸载不存在的文件不报错"""
        script = tmp_path / "nope.sh"
        uninstall_integration(script)
