"""plugins/tui/dashboard.py 测试 - L3 实时仪表盘"""
from unittest.mock import patch, MagicMock

from autosocks.plugins.tui.dashboard import render_dashboard, DashboardData


class TestDashboardData:
    """测试仪表盘数据结构"""

    def test_create_data(self):
        """创建仪表盘数据"""
        data = DashboardData(
            status="healthy",
            server="root@1.2.3.4",
            port=1080,
            exit_ip="203.0.113.50",
            latency_ms=45.2,
            uptime="2h 30m",
        )
        assert data.status == "healthy"
        assert data.port == 1080
        assert data.exit_ip == "203.0.113.50"


class TestRenderDashboard:
    """测试仪表盘渲染"""

    def test_render_returns_string(self):
        """渲染返回字符串内容"""
        data = DashboardData(
            status="healthy",
            server="root@1.2.3.4",
            port=1080,
            exit_ip="1.2.3.4",
            latency_ms=30.0,
            uptime="1h",
        )
        output = render_dashboard(data)
        assert "root@1.2.3.4" in output
        assert "1080" in output
        assert "healthy" in output

    def test_render_degraded_status(self):
        """渲染降级状态"""
        data = DashboardData(
            status="degraded",
            server="root@1.2.3.4",
            port=1080,
            exit_ip=None,
            latency_ms=-1,
            uptime="0m",
        )
        output = render_dashboard(data)
        assert "degraded" in output

    def test_render_down_status(self):
        """渲染停止状态"""
        data = DashboardData(
            status="down",
            server="root@1.2.3.4",
            port=1080,
            exit_ip=None,
            latency_ms=-1,
            uptime="0m",
        )
        output = render_dashboard(data)
        assert "down" in output
