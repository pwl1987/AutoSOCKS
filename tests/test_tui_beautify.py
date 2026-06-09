"""plugins/tui/beautify.py 测试 - L1 美化输出"""
from autosocks.plugins.tui.beautify import panel, table_row, divider


class TestPanel:
    """测试面板输出"""

    def test_panel_with_title_and_content(self, capsys):
        """面板包含标题和内容"""
        panel("AutoSOCKS 状态", ["服务器：root@1.2.3.4", "端口：1080"])
        captured = capsys.readouterr()
        assert "AutoSOCKS 状态" in captured.out
        assert "root@1.2.3.4" in captured.out
        assert "1080" in captured.out
        # 面板有上下边框
        assert "━" in captured.out

    def test_panel_single_line(self, capsys):
        """面板单行内容"""
        panel("提示", ["服务已启动"])
        captured = capsys.readouterr()
        assert "提示" in captured.out
        assert "服务已启动" in captured.out


class TestTableRow:
    """测试表格行输出"""

    def test_table_row_key_value(self, capsys):
        """表格行输出 key: value 格式"""
        table_row("服务器", "root@1.2.3.4")
        captured = capsys.readouterr()
        assert "服务器" in captured.out
        assert "root@1.2.3.4" in captured.out


class TestDivider:
    """测试分隔线"""

    def test_divider_output(self, capsys):
        """分隔线包含横线字符"""
        divider()
        captured = capsys.readouterr()
        assert "─" in captured.out or "━" in captured.out
