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
        assert len(items) >= 5
        labels = [i.label for i in items]
        assert "启动代理" in labels
        assert "停止代理" in labels
        assert "查看状态" in labels
        assert "配置服务器" in labels
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
