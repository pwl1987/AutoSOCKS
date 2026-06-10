"""plugins/update.py 测试 - 自更新"""
import json
from unittest.mock import patch, MagicMock

from autosocks.plugins.update import check_latest_version, perform_update


class TestCheckLatestVersion:
    """测试检查最新版本"""

    @patch("autosocks.plugins.update.resolve_remote", return_value="1.2.3.4")
    @patch("autosocks.plugins.update.subprocess.run")
    def test_doh_curl_path(self, mock_run, mock_resolve):
        """DoH 解析成功 → curl --resolve 路径"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"name": "v2.1.0"}]),
        )
        version = check_latest_version()
        assert version == "2.1.0"

    @patch("autosocks.plugins.update.resolve_remote", return_value="1.2.3.4")
    @patch("autosocks.plugins.update.subprocess.run")
    def test_doh_curl_returns_none_on_empty(self, mock_run, mock_resolve):
        """DoH curl 返回空列表"""
        mock_run.return_value = MagicMock(returncode=0, stdout="[]")
        version = check_latest_version()
        assert version is None

    @patch("autosocks.plugins.update.resolve_remote", return_value=None)
    @patch("autosocks.plugins.update.urllib.request.urlopen")
    def test_fallback_urllib(self, mock_urlopen, mock_resolve):
        """DoH 失败 → 回退 urllib"""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([{"name": "v3.0.0"}]).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        version = check_latest_version()
        assert version == "3.0.0"

    @patch("autosocks.plugins.update.resolve_remote", return_value=None)
    @patch("autosocks.plugins.update.urllib.request.urlopen", side_effect=Exception("network error"))
    def test_network_error_returns_none(self, mock_urlopen, mock_resolve):
        """网络错误返回 None"""
        version = check_latest_version()
        assert version is None

    @patch("autosocks.plugins.update.resolve_remote", return_value=None)
    @patch("autosocks.plugins.update.urllib.request.urlopen")
    def test_empty_response_returns_none(self, mock_urlopen, mock_resolve):
        """空响应返回 None"""
        mock_response = MagicMock()
        mock_response.read.return_value = b"[]"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        version = check_latest_version()
        assert version is None


class TestPerformUpdate:
    """测试执行更新"""

    @patch("autosocks.plugins.update.subprocess.run")
    def test_update_success(self, mock_run):
        """更新成功"""
        mock_run.return_value = MagicMock(returncode=0)
        result = perform_update()
        assert result is True
        # 确认使用 GitHub 源安装
        cmd = mock_run.call_args[0][0]
        assert "git+https://github.com/pwl1987/AutoSOCKS.git@main" in " ".join(cmd)

    @patch("autosocks.plugins.update.subprocess.run")
    def test_update_failure(self, mock_run):
        """更新失败"""
        mock_run.return_value = MagicMock(returncode=1, stderr="pip error")
        result = perform_update()
        assert result is False
