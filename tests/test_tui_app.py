"""tui/app.py 测试 - curses TUI 主界面"""
from unittest.mock import patch, MagicMock

from autosocks.plugins.tui.app import TUIApp, MenuItem


class TestMenuItem:
    """测试菜单项"""

    def test_menu_item_creation(self):
        """创建菜单项"""
        item = MenuItem("启动代理", "start")
        assert item.label == "启动代理"
        assert item.action == "start"

    def test_menu_items_default(self):
        """默认菜单项"""
        items = TUIApp.default_menu_items()
        assert len(items) == 11
        labels = [i.label for i in items]
        assert "启动代理" in labels
        assert "停止代理" in labels
        assert "重启代理" in labels
        assert "查看状态" in labels
        assert "健康检查" in labels
        assert "配置服务器" in labels
        assert "HTTP 代理" in labels
        assert "环境变量" in labels
        assert "Shell 集成" in labels
        assert "检查更新" in labels
        assert "退出" in labels


class TestTUIApp:
    """测试 TUI 应用"""

    def test_app_creation(self):
        """创建 TUI 应用"""
        app = TUIApp()
        assert app.selected == 0
        assert app.running is True

    def test_move_up(self):
        """上移光标"""
        app = TUIApp()
        app.selected = 2
        app.move_up()
        assert app.selected == 1

    def test_move_up_at_top_wraps(self):
        """在最顶部上移回到底部"""
        app = TUIApp()
        app.selected = 0
        app.move_up()
        assert app.selected == len(app.items) - 1

    def test_move_down(self):
        """下移光标"""
        app = TUIApp()
        app.selected = 0
        app.move_down()
        assert app.selected == 1

    def test_move_down_at_bottom_wraps(self):
        """在最底部下移回到顶部"""
        app = TUIApp()
        app.selected = len(app.items) - 1
        app.move_down()
        assert app.selected == 0

    def test_get_selected_action(self):
        """获取选中项的 action"""
        app = TUIApp()
        app.selected = 0
        action = app.get_selected_action()
        assert action == app.items[0].action

    def test_quit(self):
        """退出"""
        app = TUIApp()
        app.quit()
        assert app.running is False

    @patch("autosocks.plugins.tui.app.curses.wrapper")
    def test_run_calls_wrapper(self, mock_wrapper):
        """run 调用 curses.wrapper"""
        app = TUIApp()
        app.run()
        mock_wrapper.assert_called_once_with(app._main_loop)

    @patch("autosocks.plugins.tui.app.service_is_active", return_value=True)
    @patch("autosocks.plugins.tui.app.load_config")
    def test_execute_action_status(self, mock_load, mock_active):
        """execute_action 调用 status"""
        mock_load.return_value = {
            "server_user": "root",
            "server_host": "1.2.3.4",
            "local_port": 1080,
            "local_bind": "127.0.0.1",
        }
        app = TUIApp()
        app.selected = 3  # 查看状态
        app.execute_action("status")
        assert "运行中" in app.message

    @patch("autosocks.plugins.tui.app.service_is_active", return_value=False)
    def test_execute_action_health_not_running(self, mock_active):
        """健康检查 - 服务未运行"""
        app = TUIApp()
        app.execute_action("health")
        assert "未运行" in app.message

    @patch("autosocks.plugins.tui.app.load_config")
    def test_execute_action_env(self, mock_load):
        """环境变量显示"""
        mock_load.return_value = {
            "local_bind": "127.0.0.1",
            "local_port": 1080,
        }
        app = TUIApp()
        app.execute_action("env")
        assert "socks5://" in app.message

    @patch("autosocks.plugins.tui.app.service_is_active", return_value=False)
    def test_execute_action_http_proxy_not_running(self, mock_active):
        """HTTP 代理 - 服务未运行"""
        app = TUIApp()
        app.execute_action("http_proxy")
        assert "未运行" in app.message
