"""plugins/health.py 测试 - 健康检查"""
from unittest.mock import patch, MagicMock

from autosocks.plugins.health import check_health, check_latency, HealthStatus


class TestCheckHealth:
    """测试健康检查"""

    @patch("autosocks.plugins.health.check_proxy", return_value=True)
    @patch("autosocks.plugins.health.service_is_active", return_value=True)
    def test_healthy(self, mock_active, mock_proxy):
        """服务运行且代理可用"""
        result = check_health(port=1080)
        assert result.status == HealthStatus.HEALTHY
        assert result.proxy_ok is True

    @patch("autosocks.plugins.health.check_proxy", return_value=False)
    @patch("autosocks.plugins.health.service_is_active", return_value=True)
    def test_service_up_proxy_down(self, mock_active, mock_proxy):
        """服务运行但代理不可用"""
        result = check_health(port=1080)
        assert result.status == HealthStatus.DEGRADED
        assert result.proxy_ok is False

    @patch("autosocks.plugins.health.service_is_active", return_value=False)
    def test_service_down(self, mock_active):
        """服务未运行"""
        result = check_health(port=1080)
        assert result.status == HealthStatus.DOWN


class TestCheckLatency:
    """测试延迟检测"""

    @patch("autosocks.plugins.health.get_exit_ip", return_value="1.2.3.4")
    @patch("autosocks.plugins.health.subprocess.run")
    def test_latency_success(self, mock_run, mock_ip):
        """延迟检测成功"""
        mock_run.return_value = MagicMock(returncode=0, stdout="1.2.3.4\n")
        result = check_latency(port=1080, samples=3)
        assert len(result) == 3
        assert all(isinstance(t, float) for t in result)

    @patch("autosocks.plugins.health.subprocess.run")
    def test_latency_failure(self, mock_run):
        """延迟检测失败"""
        mock_run.return_value = MagicMock(returncode=1)
        result = check_latency(port=1080, samples=3)
        assert len(result) == 3
        assert all(t < 0 for t in result)
