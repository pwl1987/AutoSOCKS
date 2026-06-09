"""plugins/tui/dashboard.py 测试 - L3 实时仪表盘"""

from autosocks.plugins.tui.dashboard import render_dashboard, render_dashboard_plain, DashboardData


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

    def test_default_values(self):
        """默认值"""
        data = DashboardData(status="healthy", server="root@x", port=1080)
        assert data.bind == "127.0.0.1"
        assert data.auth_type == "key"
        assert data.reconnect is True
        assert data.log_enabled is True
        assert data.profile_name == ""


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

    def test_render_socks5_address_format(self):
        """SOCKS5 地址格式正确（bind:port 整体对齐，不是 port 单独对齐）"""
        data = DashboardData(
            status="healthy",
            server="root@1.2.3.4",
            port=1080,
        )
        output = render_dashboard(data)
        # 应包含 "127.0.0.1:1080" 而非 "127.0.0.1:1080              "（port数字被格式化）
        assert "127.0.0.1:1080" in output

    def test_render_plain_no_ansi(self):
        """纯文本渲染不含 ANSI 转义码"""
        data = DashboardData(
            status="healthy",
            server="root@1.2.3.4",
            port=1080,
        )
        output = render_dashboard_plain(data)
        assert "\033[" not in output
        assert "root@1.2.3.4" in output
        assert "1080" in output

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
