#!/bin/bash
# NTFS Mate 卸载脚本：移除全局命令与应用本体（不动 macFUSE / ntfs-3g 驱动）
set -euo pipefail

BREW_PREFIX="$(brew --prefix 2>/dev/null || echo /usr/local)"
APP_DIR="$BREW_PREFIX/opt/ntfs-mate"
BIN_LINK="$BREW_PREFIX/bin/ntfs-mate"

[ ! -e "$BIN_LINK" ] && [ ! -d "$APP_DIR" ] && { echo "未安装，无需卸载。"; exit 0; }

rm -f "$BIN_LINK" && echo "已删除全局命令：$BIN_LINK"
rm -rf "$APP_DIR" && echo "已删除应用本体：$APP_DIR"

echo "✅ 卸载完成（macFUSE 与 ntfs-3g 驱动保留；如需一并卸载：brew uninstall --cask macfuse && brew uninstall ntfs-3g-mac）"
