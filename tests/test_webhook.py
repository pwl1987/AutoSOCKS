"""plugins/webhook.py 测试 - Webhook 告警"""
from unittest.mock import patch, MagicMock
from autosocks.plugins.webhook import send_webhook


class TestSendWebhook:
    """测试发送 Webhook"""

    @patch("autosocks.plugins.webhook.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        """发送成功"""
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = send_webhook("https://example.com/hook", "test message")
        assert result is True
        mock_urlopen.assert_called_once()

    @patch("autosocks.plugins.webhook.urllib.request.urlopen", side_effect=Exception("fail"))
    def test_send_failure(self, mock_urlopen):
        """发送失败"""
        result = send_webhook("https://example.com/hook", "test message")
        assert result is False

    @patch("autosocks.plugins.webhook.urllib.request.urlopen")
    def test_send_json_payload(self, mock_urlopen):
        """发送 JSON payload"""
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = send_webhook("https://example.com/hook", "alert")
        assert result is True
