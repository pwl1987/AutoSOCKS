"""tunnel.py 测试 - SSH 隧道管理"""
from unittest.mock import patch, MagicMock

from autosocks.core.tunnel import build_ssh_command, check_proxy, get_exit_ip


class TestBuildSshCommand:
    """测试构建 SSH 命令行"""

    def test_basic_key_auth(self):
        """基本密钥认证命令"""
        config = {
            "server_host": "1.2.3.4",
            "server_user": "root",
            "server_port": 22,
            "local_port": 1080,
            "local_bind": "127.0.0.1",
            "auth_type": "key",
            "auth_key_path": "~/.ssh/id_rsa",
            "ssh_keepalive": 60,
            "ssh_timeout": 10,
        }
        cmd = build_ssh_command(config)

        assert cmd[0] == "ssh"
        assert "-D" in cmd
        assert "127.0.0.1:1080" in cmd
        assert "-N" in cmd
        assert "-p" in cmd
        assert "-i" in cmd
        assert "~/.ssh/id_rsa" in cmd
        assert "root@1.2.3.4" in cmd

    def test_password_auth_no_key_flag(self):
        """密码认证时不带 -i 参数"""
        config = {
            "server_host": "5.6.7.8",
            "server_user": "admin",
            "server_port": 2222,
            "local_port": 1081,
            "local_bind": "127.0.0.1",
            "auth_type": "password",
            "auth_key_path": "",
            "ssh_keepalive": 60,
            "ssh_timeout": 10,
        }
        cmd = build_ssh_command(config)

        assert "-i" not in cmd
        assert "admin@5.6.7.8" in cmd
        assert "-p" in cmd
        # 端口 2222 在 -p 后面
        port_idx = cmd.index("-p")
        assert cmd[port_idx + 1] == "2222"

    def test_lan_bind(self):
        """局域网绑定 0.0.0.0"""
        config = {
            "server_host": "1.2.3.4",
            "server_user": "root",
            "server_port": 22,
            "local_port": 1080,
            "local_bind": "0.0.0.0",
            "auth_type": "key",
            "auth_key_path": "~/.ssh/id_rsa",
            "ssh_keepalive": 60,
            "ssh_timeout": 10,
        }
        cmd = build_ssh_command(config)

        assert "0.0.0.0:1080" in cmd

    def test_keepalive_options(self):
        """SSH keepalive 参数"""
        config = {
            "server_host": "1.2.3.4",
            "server_user": "root",
            "server_port": 22,
            "local_port": 1080,
            "local_bind": "127.0.0.1",
            "auth_type": "key",
            "auth_key_path": "~/.ssh/id_rsa",
            "ssh_keepalive": 120,
            "ssh_timeout": 15,
        }
        cmd = build_ssh_command(config)

        assert "ServerAliveInterval=120" in cmd
        assert "ConnectTimeout=15" in cmd


class TestCheckProxy:
    """测试代理连通性检测"""

    @patch("autosocks.core.tunnel.subprocess.run")
    def test_proxy_working(self, mock_run):
        """代理连通"""
        mock_run.return_value = MagicMock(returncode=0, stdout="1.2.3.4\n")
        assert check_proxy(1080) is True

    @patch("autosocks.core.tunnel.subprocess.run")
    def test_proxy_not_working(self, mock_run):
        """代理不通"""
        mock_run.return_value = MagicMock(returncode=1)
        assert check_proxy(1080) is False


class TestGetExitIp:
    """测试获取出口 IP"""

    @patch("autosocks.core.tunnel.subprocess.run")
    def test_get_ip_success(self, mock_run):
        """成功获取出口 IP"""
        mock_run.return_value = MagicMock(returncode=0, stdout="203.0.113.50\n")
        ip = get_exit_ip(1080)
        assert ip == "203.0.113.50"

    @patch("autosocks.core.tunnel.subprocess.run")
    def test_get_ip_failure(self, mock_run):
        """获取出口 IP 失败"""
        mock_run.return_value = MagicMock(returncode=1, stderr="Connection refused")
        ip = get_exit_ip(1080)
        assert ip is None
