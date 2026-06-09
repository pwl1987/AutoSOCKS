"""plugins/proxy.py 测试 - HTTP 代理管理"""
from unittest.mock import patch, MagicMock

from autosocks.plugins.proxy import (
    detect_gost,
    generate_gost_command,
    generate_privoxy_config,
    start_http_proxy,
    stop_http_proxy,
)


class TestDetectGost:
    """测试检测 gost 安装"""

    @patch("autosocks.plugins.proxy.shutil.which", return_value="/usr/bin/gost")
    def test_gost_found(self, mock_which):
        """gost 已安装"""
        assert detect_gost() == "/usr/bin/gost"

    @patch("autosocks.plugins.proxy.shutil.which", return_value=None)
    def test_gost_not_found(self, mock_which):
        """gost 未安装"""
        assert detect_gost() is None


class TestGenerateGostCommand:
    """测试生成 gost 命令"""

    def test_basic_command(self):
        """基本 gost SOCKS5→HTTP 转发命令"""
        cmd = generate_gost_command(socks_port=1080, http_port=8080, bind="127.0.0.1")
        assert "gost" in cmd[0] or "gost" in " ".join(cmd)
        assert "1080" in " ".join(cmd)
        assert "8080" in " ".join(cmd)

    def test_lan_bind(self):
        """局域网绑定"""
        cmd = generate_gost_command(socks_port=1080, http_port=8080, bind="0.0.0.0")
        assert "0.0.0.0:8080" in " ".join(cmd)


class TestGeneratePrivoxyConfig:
    """测试生成 Privoxy 配置"""

    def test_privoxy_config_content(self):
        """配置包含 SOCKS5 转发"""
        config = generate_privoxy_config(socks_port=1080, http_port=8118, bind="127.0.0.1")
        assert "1080" in config
        assert "8118" in config
        assert "socks5" in config.lower() or "forward-socks5" in config.lower()


class TestStartHttpProxy:
    """测试启动 HTTP 代理"""

    @patch("autosocks.plugins.proxy.detect_gost", return_value="/usr/bin/gost")
    @patch("autosocks.plugins.proxy.subprocess.Popen")
    def test_start_with_gost(self, mock_popen, mock_gost):
        """使用 gost 启动"""
        mock_popen.return_value = MagicMock(pid=12345)
        result = start_http_proxy(socks_port=1080, http_port=8080)
        assert result is True
        mock_popen.assert_called_once()

    @patch("autosocks.plugins.proxy.detect_gost", return_value=None)
    def test_start_no_gost(self, mock_gost):
        """没有 gost 时返回 False"""
        result = start_http_proxy(socks_port=1080, http_port=8080)
        assert result is False


class TestStopHttpProxy:
    """测试停止 HTTP 代理"""

    @patch("autosocks.plugins.proxy.subprocess.run")
    def test_stop_success(self, mock_run):
        """停止成功"""
        mock_run.return_value = MagicMock(returncode=0)
        result = stop_http_proxy()
        assert result is True
