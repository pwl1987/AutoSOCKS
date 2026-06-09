"""plugins/geo.py 测试 - GeoIP 分流"""
from pathlib import Path
from unittest.mock import patch, MagicMock

from autosocks.plugins.geo import load_ip_list, is_china_ip, update_ip_list


class TestLoadIpList:
    """测试加载 IP 列表"""

    def test_load_valid_list(self, tmp_path: Path):
        """加载有效 IP 列表"""
        ip_file = tmp_path / "china_ips.txt"
        ip_file.write_text("1.0.1.0/24\n1.0.2.0/23\n1.0.8.0/21\n")
        networks = load_ip_list(ip_file)
        assert len(networks) == 3

    def test_load_empty_file(self, tmp_path: Path):
        """空文件返回空列表"""
        ip_file = tmp_path / "china_ips.txt"
        ip_file.write_text("")
        networks = load_ip_list(ip_file)
        assert networks == []

    def test_load_skips_comments(self, tmp_path: Path):
        """跳过注释行"""
        ip_file = tmp_path / "china_ips.txt"
        ip_file.write_text("# comment\n1.0.1.0/24\n# another\n")
        networks = load_ip_list(ip_file)
        assert len(networks) == 1


class TestIsChinaIp:
    """测试判断是否国内 IP"""

    def test_china_ip(self, tmp_path: Path):
        """国内 IP 返回 True"""
        ip_file = tmp_path / "china_ips.txt"
        ip_file.write_text("1.0.1.0/24\n")
        networks = load_ip_list(ip_file)
        assert is_china_ip("1.0.1.10", networks) is True

    def test_foreign_ip(self, tmp_path: Path):
        """国外 IP 返回 False"""
        ip_file = tmp_path / "china_ips.txt"
        ip_file.write_text("1.0.1.0/24\n")
        networks = load_ip_list(ip_file)
        assert is_china_ip("8.8.8.8", networks) is False

    def test_private_ip(self, tmp_path: Path):
        """私有 IP 不在列表中"""
        ip_file = tmp_path / "china_ips.txt"
        ip_file.write_text("1.0.1.0/24\n")
        networks = load_ip_list(ip_file)
        assert is_china_ip("192.168.1.1", networks) is False


class TestUpdateIpList:
    """测试更新 IP 列表"""

    @patch("autosocks.plugins.geo.urllib.request.urlopen")
    def test_update_downloads_file(self, mock_urlopen, tmp_path: Path):
        """下载并保存 IP 列表"""
        mock_response = MagicMock()
        mock_response.read.return_value = b"1.0.1.0/24\n1.0.2.0/23\n"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        ip_file = tmp_path / "china_ips.txt"
        result = update_ip_list(ip_file)
        assert result is True
        assert ip_file.exists()

    @patch("autosocks.plugins.geo.urllib.request.urlopen", side_effect=Exception("network"))
    def test_update_network_error(self, mock_urlopen, tmp_path: Path):
        """网络错误返回 False"""
        ip_file = tmp_path / "china_ips.txt"
        result = update_ip_list(ip_file)
        assert result is False
