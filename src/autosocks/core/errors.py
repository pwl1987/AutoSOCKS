"""错误码定义和友好提示"""
from __future__ import annotations

import sys


# 错误码 → (标题, 描述, 建议)
_ERROR_MAP: dict[str, tuple[str, str, list[str]]] = {
    "E001": (
        "权限不足",
        "需要管理员权限才能执行此操作",
        ["在命令前面加 sudo", "例如：sudo autosocks start"],
    ),
    "E002": (
        "端口被占用",
        "端口 1080 已被其他程序使用",
        ["换个端口：autosocks config --port 1081", "查看谁在用：sudo netstat -tlnp | grep 1080"],
    ),
    "E003": (
        "网络不通",
        "无法连接到服务器",
        [
            "检查网络：ping 8.8.8.8（测试网络通不通）",
            "检查地址：确认IP地址正确",
            "系管理员：确认服务器状态",
        ],
    ),
    "E004": (
        "认证失败",
        "登录服务器失败",
        [
            "检查用户名：确认服务器上有这个用户",
            "检查密钥：ls -la ~/.ssh/id_rsa",
            "手动测试：ssh root@你的服务器IP",
        ],
    ),
    "E005": (
        "服务未安装",
        "AutoSOCKS 还没有安装",
        ["先安装：autosocks install"],
    ),
    "E006": (
        "配置损坏",
        "配置文件异常，无法读取",
        [
            "查看配置：cat /etc/autosocks/config.conf",
            "重新配置：autosocks config --server user@IP",
            "如需恢复：autosocks import < 备份文件",
        ],
    ),
    "E007": (
        "SSH未安装",
        "系统没有安装 SSH 客户端",
        [
            "Ubuntu/Debian: sudo apt-get install openssh-client",
            "CentOS/RHEL: sudo yum install openssh-clients",
        ],
    ),
    "E008": (
        "systemd不可用",
        "系统不支持 systemd 服务管理",
        [
            "检查系统：cat /etc/os-release",
            "系管理员：确认系统版本",
        ],
    ),
    "E009": (
        "缺少参数",
        "在脚本中调用安装，但没有指定必要参数",
        [
            "添加参数：curl ... | sudo bash -s -- --server user@1.2.3.4",
            "查看帮助：autosocks help --all",
        ],
    ),
    "E010": (
        "密钥权限错误",
        "密钥文件权限不正确",
        [
            "修复权限：chmod 600 ~/.ssh/id_rsa",
            "然后重试：autosocks start",
        ],
    ),
    "E011": (
        "服务器SSH服务异常",
        "服务器上的 SSH 服务没有响应",
        [
            "系管理员检查SSH服务状态",
            "检查防火墙规则",
        ],
    ),
    "E012": (
        "格式错误",
        "输入的格式不正确",
        [
            "服务器地址格式：user@192.168.1.100",
            "查看帮助：autosocks help --all",
        ],
    ),
    "E013": (
        "无可回滚版本",
        "没有可回滚的旧版本",
        ["重新安装当前版本：autosocks install"],
    ),
    "E014": (
        "远程服务器未启用公钥认证",
        "远程服务器的 SSH 没有开启公钥登录功能",
        [
            "运行：autosocks check-pubkey",
            "或手动登录远程服务器修改 /etc/ssh/sshd_config",
        ],
    ),
}


def show_error(error_code: str) -> None:
    """显示错误友好提示。

    Args:
        error_code: 错误码 (E001-E014)
    """
    if error_code in _ERROR_MAP:
        title, description, suggestions = _ERROR_MAP[error_code]
    else:
        title = "未知错误"
        description = "发生了未预期的错误"
        suggestions = [
            "查看日志：autosocks logs",
            "搜索解决方案：https://github.com/pwl1987/AutoSOCKS/issues",
        ]

    # 错误标题到 stderr
    print(f"\033[0;31m❌ {title} [错误码：{error_code}]\033[0m", file=sys.stderr)
    print(file=sys.stderr)

    # 问题描述和建议到 stdout
    print(f"问题：{description}")
    print()
    print("试试这个：")
    for hint in suggestions:
        print(f"• {hint}")

    print()
    print("────────────────────────────────")
    print(f"🔍 搜索解决方案：https://github.com/pwl1987/AutoSOCKS/error/{error_code}")
    print()
