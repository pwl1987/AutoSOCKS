"""plugins/tui/menu.py 测试 - L2 交互式菜单"""
from unittest.mock import patch
from autosocks.plugins.tui.menu import select_option, input_text


class TestSelectOption:
    """测试交互式选择"""

    @patch("builtins.input", return_value="1")
    def test_select_first_option(self, mock_input):
        """选择第一个选项返回索引 0"""
        result = select_option("选择认证方式", ["密钥认证", "密码认证"])
        assert result == 0
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="2")
    def test_select_second_option(self, mock_input):
        """选择第二个选项返回索引 1"""
        result = select_option("选择认证方式", ["密钥认证", "密码认证"])
        assert result == 1

    @patch("builtins.input", side_effect=["abc", "1"])
    def test_invalid_then_valid(self, mock_input):
        """无效输入后重试"""
        result = select_option("选择", ["选项A", "选项B"])
        assert result == 0
        assert mock_input.call_count == 2

    @patch("builtins.input", return_value="")
    def test_default_option(self, mock_input):
        """空输入使用默认值"""
        result = select_option("选择", ["选项A", "选项B"], default=1)
        assert result == 1


class TestInputText:
    """测试文本输入"""

    @patch("builtins.input", return_value="root@1.2.3.4")
    def test_input_with_prompt(self, mock_input):
        """输入文本返回值"""
        result = input_text("服务器地址")
        assert result == "root@1.2.3.4"

    @patch("builtins.input", return_value="")
    def test_input_empty_with_default(self, mock_input):
        """空输入返回默认值"""
        result = input_text("端口", default="1080")
        assert result == "1080"

    @patch("builtins.input", side_effect=["", "", "1080"])
    def test_input_required_empty_retries(self, mock_input):
        """必填项空输入重试"""
        result = input_text("服务器地址", required=True)
        assert result == "1080"
        assert mock_input.call_count == 3
