#!/bin/bash
#
# 定时任务入口包装脚本
# 使用 caffeinate 防止脚本运行期间电脑休眠
# 即使在电池+合盖的 DarkWake 状态下唤醒后，
# caffeinate 会阻止系统重新休眠，直到 Python 脚本跑完
#
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# -i: 防止系统空闲休眠 (允许屏幕休眠)
# 脚本结束后 caffeinate 自动释放，电脑恢复正常休眠
exec caffeinate -i "$PYTHON_BIN" "$SCRIPT_DIR/main.py"
