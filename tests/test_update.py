"""plugins/update.py 测试 - 自更新"""
from unittest.mock import patch, MagicMock
from autosocks.plugins.update import check_latest_version, perform_update


class TestCheckLatestVersion:
    """测试检查最新版本"""

    @patch("autosocks.plugins.update.urllib.request.urlopen")
    def test_returns_version(self, mock_urlopen):
        """返回最新版本号"""
        import json
        mock_response = MagicMock()
        pypi_data = json.dumps({"info": {"version": "2.1.0"}}).encode()
        mock_response.read.return_value = pypi_data
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        version = check_latest_version()
        assert version == "2.1.0"

    @patch("autosocks.plugins.update.urllib.request.urlopen", side_effect=Exception("network error"))
    def test_network_error_returns_none(self, mock_urlopen):
        """网络错误返回 None"""
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
        mock_run.assert_called_once()

    @patch("autosocks.plugins.update.subprocess.run")
    def test_update_failure(self, mock_run):
        """更新失败"""
        mock_run.return_value = MagicMock(returncode=1, stderr="pip error")
        result = perform_update()
        assert result is False
