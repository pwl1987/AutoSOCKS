"""service.py 测试 - systemd 服务管理"""
from unittest.mock import patch, MagicMock

from autosocks.core.service import (
    service_start,
    service_stop,
    service_restart,
    service_is_active,
    SERVICE_NAME,
)


class TestServiceStart:
    """测试启动 systemd 服务"""

    @patch("autosocks.core.service.subprocess.run")
    def test_start_success(self, mock_run):
        """systemctl start 成功"""
        mock_run.return_value = MagicMock(returncode=0)
        assert service_start() is True
        mock_run.assert_called_once_with(
            ["systemctl", "start", SERVICE_NAME],
            capture_output=True, text=True,
        )

    @patch("autosocks.core.service.subprocess.run")
    def test_start_failure(self, mock_run):
        """systemctl start 失败"""
        mock_run.return_value = MagicMock(returncode=1, stderr="Job failed")
        assert service_start() is False


class TestServiceStop:
    """测试停止 systemd 服务"""

    @patch("autosocks.core.service.subprocess.run")
    def test_stop_success(self, mock_run):
        """systemctl stop 成功"""
        mock_run.return_value = MagicMock(returncode=0)
        assert service_stop() is True
        mock_run.assert_called_once_with(
            ["systemctl", "stop", SERVICE_NAME],
            capture_output=True, text=True,
        )


class TestServiceRestart:
    """测试重启 systemd 服务"""

    @patch("autosocks.core.service.subprocess.run")
    def test_restart_success(self, mock_run):
        """systemctl restart 成功"""
        mock_run.return_value = MagicMock(returncode=0)
        assert service_restart() is True
        mock_run.assert_called_once_with(
            ["systemctl", "restart", SERVICE_NAME],
            capture_output=True, text=True,
        )


class TestServiceIsActive:
    """测试检查服务状态"""

    @patch("autosocks.core.service.subprocess.run")
    def test_service_active(self, mock_run):
        """服务正在运行"""
        mock_run.return_value = MagicMock(returncode=0)
        assert service_is_active() is True

    @patch("autosocks.core.service.subprocess.run")
    def test_service_inactive(self, mock_run):
        """服务未运行"""
        mock_run.return_value = MagicMock(returncode=3)  # systemctl is-active 返回 3 表示 inactive
        assert service_is_active() is False
