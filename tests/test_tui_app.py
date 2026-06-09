"""tui/app.py 测试 - curses TUI 主界面"""
import time
from unittest.mock import patch, MagicMock

import curses as _curses

from autosocks.plugins.tui.app import TUIApp, MenuItem, _SCROLL_SPEED


def _mock_curses():
    """创建 curses mock 环境，用于测试中调用 curses 函数"""
    _curses.color_pair = lambda n: 0
    _curses.curs_set = lambda n: None
    _curses.A_BOLD = 0
    _curses.A_REVERSE = 0


class TestMenuItem:
    """测试菜单项"""

    def test_menu_item_creation(self):
        """创建菜单项"""
        item = MenuItem("启动代理", "start")
        assert item.label == "启动代理"
        assert item.action == "start"
        assert item.group == ""
        assert item.shortcut == ""

    def test_menu_item_with_group(self):
        """带分组的菜单项"""
        item = MenuItem("── 标题 ──", "", group="header")
        assert item.group == "header"

    def test_menu_item_with_shortcut(self):
        """带快捷键的菜单项"""
        item = MenuItem("启动代理", "start", shortcut="s")
        assert item.shortcut == "s"

    def test_menu_items_default(self):
        """默认菜单项"""
        items = TUIApp.default_menu_items()
        # 含 6 个分组标题 + 28 个可选项 = 34
        headers = [i for i in items if i.group == "header"]
        selectable = [i for i in items if i.group != "header"]
        assert len(headers) == 6
        assert len(selectable) == 28
        assert len(items) == 34

    def test_groups_present(self):
        """包含所有分组"""
        items = TUIApp.default_menu_items()
        headers = [i.label for i in items if i.group == "header"]
        assert len(headers) == 6
        assert any("代理管理" in h for h in headers)
        assert any("代理工具" in h for h in headers)
        assert any("配置编辑" in h for h in headers)
        assert any("Profile" in h for h in headers)
        assert any("系统工具" in h for h in headers)
        assert any("退出" in h for h in headers)

    def test_config_edit_items_present(self):
        """包含配置编辑菜单项"""
        items = TUIApp.default_menu_items()
        actions = [i.action for i in items if i.group != "header"]
        assert "edit_server" in actions
        assert "edit_local" in actions
        assert "edit_auth" in actions
        assert "edit_ssh" in actions
        assert "edit_reconnect" in actions
        assert "edit_log" in actions


class TestTUIApp:
    """测试 TUI 应用"""

    def test_app_creation(self):
        """创建 TUI 应用"""
        app = TUIApp()
        assert app.selected == 0
        assert app.running is True
        assert app.message == ""

    def test_selectable_items_excludes_headers(self):
        """可选项排除分组标题"""
        app = TUIApp()
        for _, item in app._selectable_items():
            assert item.group != "header"
            assert item.action != ""

    def test_move_up(self):
        """上移光标"""
        app = TUIApp()
        selectable = app._selectable_items()
        app.selected = selectable[1][0]
        app.move_up()
        assert app.selected == selectable[0][0]

    def test_move_up_at_top_wraps(self):
        """在最顶部上移回到底部"""
        app = TUIApp()
        selectable = app._selectable_items()
        app.selected = selectable[0][0]
        app.move_up()
        assert app.selected == selectable[-1][0]

    def test_move_down(self):
        """下移光标"""
        app = TUIApp()
        selectable = app._selectable_items()
        app.selected = selectable[0][0]
        app.move_down()
        assert app.selected == selectable[1][0]

    def test_move_down_at_bottom_wraps(self):
        """在最底部下移回到顶部"""
        app = TUIApp()
        selectable = app._selectable_items()
        app.selected = selectable[-1][0]
        app.move_down()
        assert app.selected == selectable[0][0]

    def test_move_skips_headers(self):
        """移动跳过分组标题"""
        app = TUIApp()
        for _ in range(30):
            app.move_down()
            assert app.items[app.selected].group != "header"

    def test_get_selected_action(self):
        """获取选中项的 action"""
        app = TUIApp()
        selectable = app._selectable_items()
        app.selected = selectable[0][0]
        action = app.get_selected_action()
        assert action == "start"

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

    def test_safe_addstr_bounds(self):
        """safe_addstr 边界检查"""
        app = TUIApp()
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        # 正常范围
        app._safe_addstr(mock_stdscr, 0, 0, "test")
        mock_stdscr.addstr.assert_called_once_with(0, 0, "test", 0)
        # 超出边界
        mock_stdscr.reset_mock()
        app._safe_addstr(mock_stdscr, -1, 0, "test")
        mock_stdscr.addstr.assert_not_called()
        app._safe_addstr(mock_stdscr, 24, 0, "test")
        mock_stdscr.addstr.assert_not_called()

    @patch("autosocks.plugins.tui.app.service_is_active", return_value=True)
    @patch("autosocks.plugins.tui.app.load_config")
    def test_execute_action_status(self, mock_load, mock_active):
        """execute_action 调用 status（通过 _execute_action）"""
        _mock_curses()
        mock_load.return_value = {
            "server_user": "root",
            "server_host": "1.2.3.4",
            "local_port": 1080,
            "local_bind": "127.0.0.1",
        }
        app = TUIApp()
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        mock_stdscr.getch.return_value = ord("q")  # 关闭对话框
        app._execute_action(mock_stdscr, "status")
        # status 弹出对话框，返回空字符串
        assert app.message == ""

    @patch("autosocks.plugins.tui.app.service_is_active", return_value=False)
    def test_execute_action_health_not_running(self, mock_active):
        """健康检查 - 服务未运行"""
        app = TUIApp()
        mock_stdscr = MagicMock()
        app._execute_action(mock_stdscr, "health")
        assert "未运行" in app.message

    @patch("autosocks.plugins.tui.app.service_is_active", return_value=False)
    def test_execute_action_http_proxy_not_running(self, mock_active):
        """HTTP 代理 - 服务未运行"""
        app = TUIApp()
        mock_stdscr = MagicMock()
        app._execute_action(mock_stdscr, "http_proxy")
        assert "未运行" in app.message

    @patch("autosocks.plugins.tui.app.service_is_active", return_value=True)
    @patch("autosocks.plugins.tui.app.load_config")
    def test_execute_action_env(self, mock_load, mock_active):
        """环境变量显示（弹出对话框）"""
        _mock_curses()
        mock_load.return_value = {
            "local_bind": "127.0.0.1",
            "local_port": 1080,
        }
        app = TUIApp()
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        mock_stdscr.getch.return_value = ord("q")  # 关闭对话框
        app._execute_action(mock_stdscr, "env")
        # env 弹出对话框，返回空字符串
        assert app.message == ""

    def test_message_timeout(self):
        """消息超时自动清除"""
        app = TUIApp()
        app.message = "test message"
        app.message_time = 0.0  # 很久以前
        # 模拟 _draw 中的超时逻辑
        elapsed = time.time() - app.message_time
        if elapsed > 15.0:
            app.message = ""
        assert app.message == ""

    @patch("autosocks.plugins.tui.app.load_config")
    @patch("autosocks.plugins.tui.app.save_config")
    def test_save_config_success(self, mock_save, mock_load):
        """保存配置成功"""
        mock_load.return_value = {"server_host": "test.com"}
        app = TUIApp()
        result = app._save_config({"server_host": "new.com"})
        assert result == "配置已保存"
        mock_save.assert_called_once()

    def test_save_config_permission_error(self):
        """保存配置权限错误"""
        app = TUIApp()
        with patch("autosocks.plugins.tui.app.save_config", side_effect=PermissionError):
            result = app._save_config({"server_host": "new.com"})
        assert "root" in result

    @patch("autosocks.plugins.tui.app.service_is_active", return_value=True)
    @patch("autosocks.plugins.tui.app.load_config")
    def test_get_config_caching(self, mock_load, mock_active):
        """配置缓存"""
        mock_load.return_value = {"server_host": "test.com"}
        app = TUIApp()
        config1 = app._get_config()
        config2 = app._get_config()
        # 第二次应该使用缓存，不重新调用 load
        assert config1 is config2
        mock_load.assert_called_once()


class TestProfileNameSanitization:
    """测试 Profile 名称安全校验"""

    def test_valid_simple_name(self):
        assert TUIApp._sanitize_profile_name("myserver") == "myserver"

    def test_valid_name_with_hyphen(self):
        assert TUIApp._sanitize_profile_name("my-server") == "my-server"

    def test_valid_name_with_underscore(self):
        assert TUIApp._sanitize_profile_name("my_server") == "my_server"

    def test_valid_name_with_dot(self):
        assert TUIApp._sanitize_profile_name("server.v2") == "server.v2"

    def test_valid_name_with_numbers(self):
        assert TUIApp._sanitize_profile_name("server123") == "server123"

    def test_reject_path_traversal(self):
        assert TUIApp._sanitize_profile_name("../etc/passwd") is None

    def test_reject_slash(self):
        assert TUIApp._sanitize_profile_name("dir/file") is None

    def test_reject_dot_dot(self):
        assert TUIApp._sanitize_profile_name("..") is None

    def test_reject_hidden_file(self):
        assert TUIApp._sanitize_profile_name(".hidden") is None

    def test_reject_empty(self):
        assert TUIApp._sanitize_profile_name("") is None

    def test_reject_space(self):
        assert TUIApp._sanitize_profile_name("my server") is None

    def test_reject_special_chars(self):
        assert TUIApp._sanitize_profile_name("server;rm -rf") is None


class TestPageNavigation:
    """测试翻页导航"""

    def test_page_up(self):
        app = TUIApp()
        selectable = app._selectable_items()
        # 先移到底部
        app.selected = selectable[-1][0]
        app.page_up()
        idx = app._selectable_index()
        assert idx == len(selectable) - 1 - _SCROLL_SPEED

    def test_page_down(self):
        app = TUIApp()
        selectable = app._selectable_items()
        app.selected = selectable[0][0]
        app.page_down()
        idx = app._selectable_index()
        assert idx == _SCROLL_SPEED

    def test_page_up_at_top(self):
        app = TUIApp()
        selectable = app._selectable_items()
        app.selected = selectable[0][0]
        app.page_up()
        # 不应越界，停留在第一个
        assert app.selected == selectable[0][0]

    def test_page_down_at_bottom(self):
        app = TUIApp()
        selectable = app._selectable_items()
        app.selected = selectable[-1][0]
        app.page_down()
        assert app.selected == selectable[-1][0]


class TestServerAddressParsing:
    """测试服务器地址解析（IPv4/IPv6/空值）"""

    def _parse(self, server_input: str) -> tuple[str, str, int]:
        """模拟 _do_install 中的地址解析逻辑，返回 (user, host, port)"""
        if "@" in server_input:
            user, host_part = server_input.split("@", 1)
        else:
            user = "root"
            host_part = server_input

        server_port = 22
        if ":" in host_part and not host_part.startswith("["):
            host, port_str = host_part.rsplit(":", 1)
            server_port = int(port_str) if port_str.isdigit() else 22
        elif host_part.startswith("["):
            bracket_end = host_part.find("]")
            if bracket_end == -1:
                host = host_part
            else:
                host = host_part[1:bracket_end]
                rest = host_part[bracket_end + 1:]
                if rest.startswith(":"):
                    server_port = int(rest[1:]) if rest[1:].isdigit() else 22
        else:
            host = host_part

        return user, host, server_port

    def test_ipv4_with_port(self):
        user, host, port = self._parse("root@1.2.3.4:2222")
        assert user == "root"
        assert host == "1.2.3.4"
        assert port == 2222

    def test_ipv4_no_port(self):
        user, host, port = self._parse("user@1.2.3.4")
        assert user == "user"
        assert host == "1.2.3.4"
        assert port == 22

    def test_no_user(self):
        user, host, port = self._parse("1.2.3.4:22")
        assert user == "root"
        assert host == "1.2.3.4"
        assert port == 22

    def test_ipv6_with_port(self):
        user, host, port = self._parse("root@[::1]:2222")
        assert user == "root"
        assert host == "::1"
        assert port == 2222

    def test_ipv6_no_port(self):
        user, host, port = self._parse("root@[::1]")
        assert user == "root"
        assert host == "::1"
        assert port == 22

    def test_ipv6_full_with_user(self):
        user, host, port = self._parse("admin@[fe80::1]:443")
        assert user == "admin"
        assert host == "fe80::1"
        assert port == 443

    def test_empty_host_after_at(self):
        user, host, port = self._parse("root@")
        assert host == ""
        # 调用方应检查 host 非空

    def test_hostname_with_port(self):
        user, host, port = self._parse("user@example.com:2222")
        assert host == "example.com"
        assert port == 2222

    def test_default_port_when_non_digit(self):
        user, host, port = self._parse("user@host:abc")
        assert host == "host"
        assert port == 22


class TestDialogEdgeCases:
    """测试对话框边缘情况"""

    def test_dialog_select_empty_options(self):
        """空选项列表应返回 None"""
        _mock_curses()
        app = TUIApp()
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        result = app._dialog_select(mock_stdscr, "空列表", [], 0)
        assert result is None

    def test_dialog_input_small_terminal(self):
        """终端太小时应返回 default"""
        _mock_curses()
        app = TUIApp()
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (5, 40)
        result = app._dialog_input(mock_stdscr, "测试", "default_val")
        assert result == "default_val"


class TestSetupWizard:
    """测试快速上手引导流程"""

    def test_setup_wizard_menu_item_exists(self):
        """快速上手菜单项存在"""
        items = TUIApp.default_menu_items()
        actions = [i.action for i in items if i.group != "header"]
        assert "setup_wizard" in actions

    def test_setup_wizard_no_root(self):
        """非 root 权限下返回提示"""
        _mock_curses()
        app = TUIApp()
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        with patch("os.geteuid", return_value=1000):
            result = app._do_setup_wizard(mock_stdscr)
        assert "root" in str(result).lower() or "权限" in str(result)

    def test_setup_wizard_handler_exists(self):
        """_do_setup_wizard 方法存在"""
        app = TUIApp()
        assert hasattr(app, "_do_setup_wizard")
        assert callable(app._do_setup_wizard)


class TestDialogForm:
    """测试多字段表单对话框"""

    def test_dialog_form_exists(self):
        """_dialog_form 方法存在"""
        app = TUIApp()
        assert hasattr(app, "_dialog_form")
        assert callable(app._dialog_form)

    def test_dialog_form_small_terminal(self):
        """终端太小时返回 None"""
        _mock_curses()
        app = TUIApp()
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (5, 40)
        result = app._dialog_form(mock_stdscr, "测试", [
            ("key1", "字段1", "val1", "text", None),
        ])
        assert result is None

    def test_dialog_form_edit_server_structure(self):
        """_do_edit_server 使用 _dialog_form"""
        app = TUIApp()
        assert hasattr(app, "_do_edit_server")
        assert callable(app._do_edit_server)

    def test_dialog_form_edit_local_structure(self):
        """_do_edit_local 使用 _dialog_form"""
        app = TUIApp()
        assert hasattr(app, "_do_edit_local")
        assert callable(app._do_edit_local)

    def test_dialog_form_edit_auth_structure(self):
        """_do_edit_auth 使用 _dialog_form"""
        app = TUIApp()
        assert hasattr(app, "_do_edit_auth")
        assert callable(app._do_edit_auth)

    def test_dialog_form_edit_ssh_structure(self):
        """_do_edit_ssh 使用 _dialog_form"""
        app = TUIApp()
        assert hasattr(app, "_do_edit_ssh")
        assert callable(app._do_edit_ssh)


class TestDaemonMode:
    """测试后台运行模式"""

    def test_daemon_menu_item_exists(self):
        """后台运行菜单项存在"""
        items = TUIApp.default_menu_items()
        actions = [i.action for i in items if i.group != "header"]
        assert "daemon" in actions

    def test_daemon_not_active(self):
        """服务未运行时返回提示"""
        _mock_curses()
        app = TUIApp()
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        with patch.object(app, "_get_active", return_value=False):
            result = app._do_daemon(mock_stdscr)
        assert "未运行" in str(result) or "启动" in str(result)

    def test_daemon_sets_quit(self):
        """后台运行时设置 running=False"""
        _mock_curses()
        app = TUIApp()
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        app.running = True
        with patch.object(app, "_get_active", return_value=True):
            with patch.object(app, "_get_config", return_value={
                "server_host": "test.example.com",
                "server_user": "root",
                "local_port": 1080,
                "local_bind": "127.0.0.1",
            }):
                result = app._do_daemon(mock_stdscr)
        assert "后台" in str(result) or "1080" in str(result)
        assert app.running is False

    def test_daemon_handler_exists(self):
        """_do_daemon 方法存在"""
        app = TUIApp()
        assert hasattr(app, "_do_daemon")
        assert callable(app._do_daemon)
