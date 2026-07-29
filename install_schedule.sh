#!/bin/bash
#
# 安装/卸载定时任务
# 用法:
#   ./install_schedule.sh        安装定时任务
#   ./install_schedule.sh remove 卸载定时任务
#
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="${PROJECT_DIR}/com.beijing.dashboard-monitor.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.beijing.dashboard-monitor.plist"
LABEL="com.beijing.dashboard-monitor"

if [ "$1" = "remove" ] || [ "$1" = "uninstall" ]; then
    echo "卸载定时任务..."
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    rm -f "$PLIST_DST"
    echo "已卸载: $LABEL"
    exit 0
fi

echo "安装定时任务..."
echo "项目目录: $PROJECT_DIR"

# 确保目录存在
mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "${PROJECT_DIR}/logs"
mkdir -p "${PROJECT_DIR}/exports"
mkdir -p "${PROJECT_DIR}/data"

# 替换 plist 中的路径占位符
sed "s|__PROJECT_DIR__|${PROJECT_DIR}|g" "$PLIST_SRC" > "$PLIST_DST"

echo "plist 已生成: $PLIST_DST"

# 如果已加载，先卸载
launchctl unload "$PLIST_DST" 2>/dev/null || true

# 加载定时任务
launchctl load "$PLIST_DST"

echo ""
echo "✓ 定时任务已安装"
echo "  执行时间: 每周一、三、六 09:00"
echo "  脚本路径: ${PROJECT_DIR}/monitor/main.py"
echo "  日志目录: ${PROJECT_DIR}/logs/"
echo "  Excel输出: ${PROJECT_DIR}/exports/"
echo ""
echo "如需手动执行一次: cd ${PROJECT_DIR}/monitor && python3 main.py"
echo "如需卸载: ./install_schedule.sh remove"
