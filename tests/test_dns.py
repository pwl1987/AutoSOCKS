"""core/dns.py 测试 - DoH 远程 DNS 解析"""
import json
import subprocess
from unittest.mock import patch, MagicMock

from autosocks.core.dns import resolve_remote, clear_cache, _is_ip


class TestIsIp:
    """测试 IP 地址判断"""

    def test_valid_ipv4(self):
        assert _is_ip("1.2.3.4") is True

    def test_valid_localhost(self):
        assert _is_ip("127.0.0.1") is True

    def test_domain_name(self):
        assert _is_ip("api.openai.com") is False

    def test_empty(self):
        assert _is_ip("") is False


class TestResolveRemote:
    """测试远程 DNS 解析"""

    def setup_method(self):
        clear_cache()

    def test_ip_passthrough(self):
        """IP 地址直接返回"""
        assert resolve_remote("1.2.3.4") == "1.2.3.4"

    @patch("autosocks.core.dns._query_doh", return_value="172.66.0.243")
    def test_doh_success(self, mock_doh):
        """DoH 解析成功"""
        result = resolve_remote("api.openai.com")
        assert result == "172.66.0.243"

    @patch("autosocks.core.dns._query_doh", return_value="172.66.0.243")
    def test_cache_hit(self, mock_doh):
        """缓存命中不重复查询"""
        r1 = resolve_remote("api.openai.com")
        r2 = resolve_remote("api.openai.com")
        assert r1 == r2 == "172.66.0.243"
        assert mock_doh.call_count == 1  # 只查一次

    @patch("autosocks.core.dns._query_doh", return_value=None)
    @patch("autosocks.core.dns._fallback_getent", return_value="10.0.0.1")
    def test_fallback_getent(self, mock_getent, mock_doh):
        """DoH 全失败 → getent 回退"""
        result = resolve_remote("example.com")
        assert result == "10.0.0.1"

    @patch("autosocks.core.dns._query_doh", return_value=None)
    @patch("autosocks.core.dns._fallback_getent", return_value=None)
    def test_all_fail(self, mock_getent, mock_doh):
        """全部失败返回 None"""
        result = resolve_remote("nonexistent.invalid")
        assert result is None


class TestQueryDoh:
    """测试单次 DoH 查询"""

    def setup_method(self):
        clear_cache()

    @patch("autosocks.core.dns.subprocess.run")
    def test_parse_a_record(self, mock_run):
        """正确解析 A 记录"""
        from autosocks.core.dns import _query_doh
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"Answer": [{"type": 1, "data": "172.66.0.243"}]}),
        )
        result = _query_doh("api.openai.com", "https://1.1.1.1/dns-query", None, 5.0)
        assert result == "172.66.0.243"

    @patch("autosocks.core.dns.subprocess.run")
    def test_no_answer(self, mock_run):
        """无 Answer 段"""
        from autosocks.core.dns import _query_doh
        mock_run.return_value = MagicMock(returncode=0, stdout='{"Status":3}')
        result = _query_doh("nonexistent.invalid", "https://1.1.1.1/dns-query", None, 5.0)
        assert result is None

    @patch("autosocks.core.dns.subprocess.run", side_effect=subprocess.TimeoutExpired("curl", 5))
    def test_exception(self, mock_run):
        """超时返回 None"""
        from autosocks.core.dns import _query_doh
        result = _query_doh("api.openai.com", "https://1.1.1.1/dns-query", None, 5.0)
        assert result is None

    @patch("autosocks.core.dns.subprocess.run")
    def test_with_proxy_port(self, mock_run):
        """带代理端口时 curl 命令含 --socks5-hostname"""
        from autosocks.core.dns import _query_doh
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"Answer": [{"type": 1, "data": "1.2.3.4"}]}),
        )
        _query_doh("test.com", "https://1.1.1.1/dns-query", 1080, 5.0)
        cmd = mock_run.call_args[0][0]
        assert "--socks5-hostname" in cmd
        assert "127.0.0.1:1080" in cmd
