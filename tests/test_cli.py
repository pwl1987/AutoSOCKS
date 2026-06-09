"""cli.py 测试 - 命令行分发"""
from unittest.mock import patch, MagicMock

from autosocks.cli import main


class TestCliHelp:
    """测试帮助命令"""

    def test_no_args_shows_help(self, capsys):
        """无参数时显示帮助"""
        with patch("sys.argv", ["autosocks"]):
            main()
        captured = capsys.readouterr()
        assert "AutoSOCKS" in captured.out

    def test_help_flag(self, capsys):
        """--help 显示帮助"""
        with patch("sys.argv", ["autosocks", "help"]):
            main()
        captured = capsys.readouterr()
        assert "AutoSOCKS" in captured.out


class TestCliVersion:
    """测试版本命令"""

    def test_version_output(self, capsys):
        """version 命令输出版本号"""
        with patch("sys.argv", ["autosocks", "version"]):
            main()
        captured = capsys.readouterr()
        assert "2.0.0" in captured.out


class TestCliStart:
    """测试 start 命令分发"""

    @patch("autosocks.cli.service_is_active", return_value=False)
    @patch("autosocks.cli.service_start", return_value=True)
    @patch("autosocks.cli.load_config")
    @patch("autosocks.cli.check_root", return_value=True)
    def test_start_calls_service_start(self, mock_root, mock_load, mock_start, mock_active):
        """start 命令调用 service_start"""
        mock_load.return_value = {
            "server_host": "1.2.3.4",
            "server_user": "root",
            "server_port": 22,
            "local_port": 1080,
            "local_bind": "127.0.0.1",
        }
        with patch("sys.argv", ["autosocks", "start"]):
            main()
        mock_start.assert_called_once()


class TestCliStop:
    """测试 stop 命令分发"""

    @patch("autosocks.cli.service_is_active", return_value=True)
    @patch("autosocks.cli.service_stop", return_value=True)
    @patch("autosocks.cli.load_config")
    @patch("autosocks.cli.check_root", return_value=True)
    def test_stop_calls_service_stop(self, mock_root, mock_load, mock_stop, mock_active):
        """stop 命令调用 service_stop"""
        mock_load.return_value = {}
        with patch("sys.argv", ["autosocks", "stop"]):
            main()
        mock_stop.assert_called_once()


class TestCliStatus:
    """测试 status 命令"""

    @patch("autosocks.cli.service_is_active", return_value=True)
    @patch("autosocks.cli.load_config")
    @patch("autosocks.cli.check_root", return_value=True)
    def test_status_running(self, mock_root, mock_load, mock_active, capsys):
        """status 显示运行中"""
        mock_load.return_value = {
            "server_host": "1.2.3.4",
            "server_user": "root",
            "local_port": 1080,
        }
        with patch("sys.argv", ["autosocks", "status"]):
            main()
        captured = capsys.readouterr()
        assert "运行中" in captured.out or "running" in captured.out.lower()


class TestCliUnknownCommand:
    """测试未知命令"""

    def test_unknown_command_exits_with_error(self, capsys):
        """未知命令输出错误"""
        with patch("sys.argv", ["autosocks", "foobar"]):
            try:
                main()
            except SystemExit:
                pass
        captured = capsys.readouterr()
        assert "未知" in captured.err or "unknown" in captured.err.lower()
