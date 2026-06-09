#!/bin/bash
# AutoSOCKS 安装器
# 用法：curl -fsSL https://raw.githubusercontent.com/pwl1987/AutoSOCKS/main/install.sh | sudo bash -s -- --server user@1.2.3.4
#
# 功能：
#   1. 检测 Python 3.10+
#   2. 创建 venv
#   3. pip install autosocks
#   4. 生成 systemd unit 文件
#   5. 可选：交互式配置服务器地址

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

# 解析参数
while [ $# -gt 0 ]; do
    case "$1" in
        --server)
            SERVER_ARG="$2"
            shift 2
            ;;
        --help)
            echo "用法：curl ... | sudo bash -s -- [--server user@1.2.3.4]"
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数：$1${NC}" >&2
            exit 1
            ;;
    esac
done

# ==================== 预检查 ====================

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

# ==================== 安装 ====================

echo ""
echo "📦 开始安装..."

# 创建 venv
if [ ! -d "$AUTOSOCKS_VENV" ]; then
    echo "  创建虚拟环境: $AUTOSOCKS_VENV"
    "$PYTHON_CMD" -m venv "$AUTOSOCKS_VENV"
fi

# 安装 autosocks
echo "  安装 autosocks 包..."
"$AUTOSOCKS_VENV/bin/pip" install --quiet --upgrade autosocks 2>/dev/null || {
    # 如果 pip 从 PyPI 安装失败，尝试从本地安装
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
        echo "  从本地源码安装..."
        "$AUTOSOCKS_VENV/bin/pip" install --quiet "$SCRIPT_DIR"
    else
        echo -e "${RED}❌ 安装失败，请检查网络连接${NC}" >&2
        exit 1
    fi
}

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
