"""errors.py 测试 - 错误码映射和友好提示"""

from autosocks.core.errors import show_error


class TestShowError:
    """测试错误码映射"""

    def test_e001_permission_denied(self, capsys):
        """E001 权限不足"""
        show_error("E001")
        captured = capsys.readouterr()
        assert "权限不足" in captured.err
        assert "E001" in captured.err
        assert "sudo" in captured.out

    def test_e002_port_in_use(self, capsys):
        """E002 端口被占用"""
        show_error("E002")
        captured = capsys.readouterr()
        assert "端口被占用" in captured.err
        assert "E002" in captured.err

    def test_e003_network_error(self, capsys):
        """E003 网络不通"""
        show_error("E003")
        captured = capsys.readouterr()
        assert "网络不通" in captured.err
        assert "ping" in captured.out.lower()

    def test_unknown_error_code(self, capsys):
        """未知错误码"""
        show_error("E999")
        captured = capsys.readouterr()
        assert "未知错误" in captured.err

    def test_output_contains_error_url(self, capsys):
        """输出包含错误码 URL"""
        show_error("E001")
        captured = capsys.readouterr()
        assert "E001" in captured.out
