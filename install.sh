#!/bin/bash
# AutoSOCKS 安装器
# 用法：
#   远程安装：curl -fsSL https://raw.githubusercontent.com/pwl1987/AutoSOCKS/main/install.sh | sudo bash
#   本地安装：sudo bash install.sh --local
#   指定服务器：sudo bash install.sh --server user@1.2.3.4
#   卸载：      sudo bash install.sh --uninstall

set -euo pipefail

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

# 路径
AUTOSOCKS_VENV="/opt/autosocks"
AUTOSOCKS_BIN="/usr/local/bin/autosocks"
SERVICE_FILE="/etc/systemd/system/autosocks.service"
CONFIG_DIR="/etc/autosocks"

# 参数
SERVER_ARG=""
LOCAL_INSTALL=false
DO_UNINSTALL=false

# 解析参数
while [ $# -gt 0 ]; do
    case "$1" in
        --server)
            SERVER_ARG="$2"
            shift 2
            ;;
        --local)
            LOCAL_INSTALL=true
            shift
            ;;
        --uninstall)
            DO_UNINSTALL=true
            shift
            ;;
        --help)
            echo "用法："
            echo "  sudo bash install.sh              # 从 GitHub 安装"
            echo "  sudo bash install.sh --local       # 从本地源码安装"
            echo "  sudo bash install.sh --server user@host"
            echo "  sudo bash install.sh --uninstall   # 卸载"
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数：$1${NC}" >&2
            exit 1
            ;;
    esac
done

# ==================== 卸载 ====================

if [ "$DO_UNINSTALL" = true ]; then
    echo -e "${YELLOW}AutoSOCKS 卸载器${NC}"
    echo ""

    if [ "$(id -u)" -ne 0 ]; then
        echo -e "${RED}❌ 需要 root 权限${NC}" >&2
        exit 1
    fi

    # 停止服务
    if systemctl is-active --quiet autosocks 2>/dev/null; then
        echo "  停止 autosocks 服务..."
        systemctl stop autosocks
    fi

    # 禁用服务
    if systemctl is-enabled --quiet autosocks 2>/dev/null; then
        echo "  禁用 autosocks 服务..."
        systemctl disable autosocks
    fi

    # 删除 systemd unit
    if [ -f "$SERVICE_FILE" ]; then
        echo "  删除 systemd 服务文件"
        rm -f "$SERVICE_FILE"
        systemctl daemon-reload
    fi

    # 删除 wrapper 脚本
    if [ -f "$AUTOSOCKS_BIN" ]; then
        echo "  删除启动脚本: $AUTOSOCKS_BIN"
        rm -f "$AUTOSOCKS_BIN"
    fi

    # 删除 venv
    if [ -d "$AUTOSOCKS_VENV" ]; then
        echo "  删除虚拟环境: $AUTOSOCKS_VENV"
        rm -rf "$AUTOSOCKS_VENV"
    fi

    # 询问是否删除配置
    if [ -d "$CONFIG_DIR" ]; then
        echo ""
        read -rp "是否删除配置文件 $CONFIG_DIR？[y/N] " CONFIRM
        if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
            echo "  删除配置目录: $CONFIG_DIR"
            rm -rf "$CONFIG_DIR"
        else
            echo "  保留配置目录: $CONFIG_DIR"
        fi
    fi

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  AutoSOCKS 已卸载${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
fi

# ==================== 安装 ====================

echo -e "${GREEN}AutoSOCKS 安装器${NC}"
echo ""

# 检查 root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}❌ 需要 root 权限，请使用 sudo${NC}" >&2
    exit 1
fi

# 检测 Python 3.10+
echo "🔍 检测 Python 环境..."
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VERSION=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            echo "  找到 Python $PY_VERSION ($cmd)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ 需要 Python 3.10+，当前系统未找到合适版本${NC}" >&2
    echo ""
    echo "安装 Python 3.10+:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-venv"
    echo "  CentOS/RHEL:   sudo yum install python3"
    exit 1
fi

# 检查 systemd
if ! command -v systemctl &>/dev/null; then
    echo -e "${RED}❌ 需要 systemd 支持${NC}" >&2
    exit 1
fi

echo ""
echo "📦 开始安装..."

# 创建 venv
if [ ! -d "$AUTOSOCKS_VENV" ]; then
    echo "  创建虚拟环境: $AUTOSOCKS_VENV"
    "$PYTHON_CMD" -m venv "$AUTOSOCKS_VENV"
fi

# 安装 autosocks
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$LOCAL_INSTALL" = true ]; then
    # 从本地源码安装
    echo "  从本地源码安装: $SCRIPT_DIR"
    "$AUTOSOCKS_VENV/bin/pip" install --quiet "$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    # 检测到本地源码，优先本地安装
    echo "  检测到本地源码，从本地安装: $SCRIPT_DIR"
    "$AUTOSOCKS_VENV/bin/pip" install --quiet "$SCRIPT_DIR"
else
    # 从 GitHub 安装
    echo "  从 GitHub 安装最新版..."
    if ! "$AUTOSOCKS_VENV/bin/pip" install --quiet --upgrade "autosocks @ git+https://github.com/pwl1987/AutoSOCKS.git@main"; then
        echo -e "${RED}❌ 安装失败，请检查网络连接${NC}" >&2
        exit 1
    fi
fi

# 创建 wrapper 脚本
echo "  创建启动脚本: $AUTOSOCKS_BIN"
cat > "$AUTOSOCKS_BIN" << EOF
#!/bin/bash
exec $AUTOSOCKS_VENV/bin/python -m autosocks "\$@"
EOF
chmod +x "$AUTOSOCKS_BIN"

# 创建配置目录
mkdir -p "$CONFIG_DIR"

# 生成 systemd unit 文件
echo "  生成 systemd 服务文件"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=AutoSOCKS SOCKS5 Proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$AUTOSOCKS_VENV/bin/python -m autosocks --daemon
Restart=always
RestartSec=3
Environment=AUTOSOCKS_CONFIG_DIR=$CONFIG_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# ==================== 配置 ====================

if [ -n "$SERVER_ARG" ]; then
    echo ""
    echo "⚙️  配置服务器地址: $SERVER_ARG"
    "$AUTOSOCKS_BIN" config --server "$SERVER_ARG"
fi

# ==================== 完成 ====================

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  AutoSOCKS 安装完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "下一步："
echo "  autosocks install    # 交互式配置服务器"
echo "  autosocks start      # 启动代理"
echo ""
