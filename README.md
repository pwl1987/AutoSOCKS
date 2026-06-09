# AutoSOCKS v2.0.0

极简 Linux SSH SOCKS5 代理管理工具，Python 重写版。

## 功能特性

- **一行安装**：`curl | bash` 安装体验，自动检测 Python 环境
- **SOCKS5 代理**：基于 SSH `-D` 动态端口转发
- **HTTP 代理**：支持 gost SOCKS5→HTTP 转换（可选 Privoxy）
- **服务管理**：systemd 守护进程，开机自启，自动重连
- **健康检查**：服务状态 + 代理可用性 + 延迟采样
- **GeoIP 分流**：基于 CIDR IP 列表的国内外流量分流
- **多 Profile**：`~/.autosocks.d/` 多服务器配置管理
- **Webhook 告警**：JSON POST 推送到外部服务
- **Shell 集成**：`eval $(autosocks env)` 自动设置代理环境变量
- **自更新**：检查 PyPI 最新版本，一键升级
- **TUI 界面**：美化面板、交互式菜单、实时仪表盘
- **零依赖**：纯 Python 标准库，无第三方运行时依赖

## 快速开始

### 安装

```bash
# 一行安装（推荐）
curl -fsSL https://raw.githubusercontent.com/pwl1987/AutoSOCKS/main/install.sh | sudo bash

# 或指定服务器地址
curl -fsSL https://raw.githubusercontent.com/pwl1987/AutoSOCKS/main/install.sh | sudo bash -s -- --server root@1.2.3.4

# 或从源码安装
git clone https://github.com/pwl1987/AutoSOCKS.git
cd AutoSOCKS
pip install -e .
```

### 常用命令

```bash
autosocks status              # 查看状态
autosocks start               # 启动代理
autosocks stop                # 停止代理
autosocks restart             # 重启代理
autosocks version             # 显示版本
autosocks help                # 查看帮助
```

### 环境变量

```bash
# 自动设置代理环境变量
eval "$(autosocks env)"

# 添加到 ~/.bashrc 实现自动设置
echo 'eval "$(autosocks env 2>/dev/null)"' >> ~/.bashrc

# 取消代理
eval "$(autosocks env unset)"
```

## 项目结构

```
src/autosocks/
├── __init__.py
├── __main__.py
├── cli.py                      # 命令分发 (match/case)
├── core/
│   ├── config.py               # INI 配置管理
│   ├── errors.py               # 错误码 E001-E014
│   ├── output.py               # 终端输出
│   ├── service.py              # systemd 操作
│   └── tunnel.py               # SSH 隧道管理
├── plugins/
│   ├── env.py                  # 环境变量
│   ├── geo.py                  # GeoIP 分流
│   ├── health.py               # 健康检查
│   ├── profile.py              # 多 Profile 管理
│   ├── proxy.py                # HTTP 代理 (gost/privoxy)
│   ├── shell_integration.py    # Shell 集成
│   ├── update.py               # 自更新
│   ├── webhook.py              # Webhook 告警
│   └── tui/
│       ├── beautify.py         # L1 美化面板
│       ├── menu.py             # L2 交互式菜单
│       └── dashboard.py        # L3 实时仪表盘
└── utils/
install.sh                      # Bash 安装器
```

## 系统要求

- Linux（支持 systemd）
- Python 3.10+
- SSH 客户端
- curl

### 可选依赖

- `gost`：HTTP 代理（SOCKS5→HTTP 转换）
- `privoxy`：HTTP 代理（备选方案）
- `textual`：完整 TUI 界面（`pip install autosocks[tui]`）

## 配置

配置文件位于 `/etc/autosocks/config.conf`（INI 格式）：

```ini
[server]
host = your-server.com
user = root
port = 22

[local]
port = 1080
bind = 127.0.0.1

[auth]
type = key
key_path = ~/.ssh/id_rsa

[ssh]
keepalive = 60
timeout = 10

[reconnect]
enabled = true
interval = 3

[log]
enabled = true
max_size = 1048576
```

## 开发

```bash
# 设置开发环境
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 代码检查
ruff check src/
mypy src/ --ignore-missing-imports
```

## 从 v1.0.0 迁移

v2.0.0 会自动将旧的 `KEY="value"` 配置转换为 INI 格式。安装时运行：

```bash
sudo bash install.sh
```

## 许可证

MIT License
