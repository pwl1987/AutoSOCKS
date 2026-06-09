"""output.py 测试 - 颜色输出函数"""
import io
import os

from autosocks.core.output import print_success, print_error, print_warning, print_info


class TestPrintFunctions:
    """测试输出函数"""

    def test_print_success(self, capsys):
        """print_success 输出绿色勾号 + 消息"""
        print_success("代理已启动")
        captured = capsys.readouterr()
        assert "代理已启动" in captured.out
        assert "✅" in captured.out

    def test_print_error_to_stderr(self, capsys):
        """print_error 输出到 stderr"""
        print_error("连接失败")
        captured = capsys.readouterr()
        assert "连接失败" in captured.err
        assert "❌" in captured.err
        assert captured.out == ""

    def test_print_error_with_code(self, capsys):
        """print_error 带错误码"""
        print_error("权限不足", "E001")
        captured = capsys.readouterr()
        assert "权限不足" in captured.err
        assert "E001" in captured.err

    def test_print_warning(self, capsys):
        """print_warning 输出黄色警告"""
        print_warning("服务已在运行")
        captured = capsys.readouterr()
        assert "服务已在运行" in captured.out
        assert "⚠️" in captured.out

    def test_print_info(self, capsys):
        """print_info 输出蓝色提示"""
        print_info("配置已完成")
        captured = capsys.readouterr()
        assert "配置已完成" in captured.out
        assert "💡" in captured.out

    def test_no_color_env(self, monkeypatch, capsys):
        """NO_COLOR=1 时不含 ANSI 转义序列"""
        monkeypatch.setenv("NO_COLOR", "1")
        # 需要重新触发模块级颜色检测
        from autosocks.core import output
        output._init_colors()
        print_success("测试")
        captured = capsys.readouterr()
        # 不应包含 ANSI escape 序列
        assert "\033[" not in captured.out
        # 但消息内容仍然存在
        assert "测试" in captured.out
