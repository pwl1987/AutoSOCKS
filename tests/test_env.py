"""plugins/env.py 测试 - 环境变量设置"""
from autosocks.plugins.env import env_set, env_unset


class TestEnvSet:
    """测试设置代理环境变量"""

    def test_env_set_output(self, capsys):
        """env_set 输出 export 命令"""
        env_set("127.0.0.1", 1080)
        captured = capsys.readouterr()
        assert "export" in captured.out
        assert "http_proxy" in captured.out
        assert "https_proxy" in captured.out
        assert "127.0.0.1:1080" in captured.out

    def test_env_set_all_proxy(self, capsys):
        """env_set 包含 ALL_PROXY"""
        env_set("127.0.0.1", 1080)
        captured = capsys.readouterr()
        assert "ALL_PROXY" in captured.out or "all_proxy" in captured.out

    def test_env_set_no_proxy(self, capsys):
        """env_set 包含 no_proxy"""
        env_set("127.0.0.1", 1080)
        captured = capsys.readouterr()
        assert "no_proxy" in captured.out


class TestEnvUnset:
    """测试清除代理环境变量"""

    def test_env_unset_output(self, capsys):
        """env_unset 输出 unset 命令"""
        env_unset()
        captured = capsys.readouterr()
        assert "unset" in captured.out
        assert "http_proxy" in captured.out
        assert "https_proxy" in captured.out
