#!/bin/bash
# NTFS Mate 卸载脚本
#   默认：仅移除 ntfs-mate 自身（全局命令 + 应用本体），保留 macFUSE / ntfs-3g 驱动
#   --all：额外卸载 macFUSE 与 ntfs-3g（完整清理，适合彻底不用 NTFS 读写）
set -euo pipefail

FULL_UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --all) FULL_UNINSTALL=1 ;;
    -h|--help) echo "用法：./uninstall.sh [--all]"; echo "  --all  一并卸载 macFUSE 与 ntfs-3g（完整清理）"; exit 0 ;;
    *) echo "未知参数：$arg（仅支持 --all）" >&2; exit 1 ;;
  esac
done

BREW_PREFIX="$(brew --prefix 2>/dev/null || echo /usr/local)"
APP_DIR="$BREW_PREFIX/opt/ntfs-mate"
BIN_LINK="$BREW_PREFIX/bin/ntfs-mate"

if [ ! -e "$BIN_LINK" ] && [ ! -d "$APP_DIR" ]; then
  echo "未检测到 ntfs-mate 安装。"
  [ "$FULL_UNINSTALL" -eq 0 ] && exit 0
else
  rm -f "$BIN_LINK" && echo "已删除全局命令：$BIN_LINK"
  rm -rf "$APP_DIR" && echo "已删除应用本体：$APP_DIR"
  echo "✅ ntfs-mate 已卸载（macFUSE / ntfs-3g 驱动保留）。"
fi

if [ "$FULL_UNINSTALL" -eq 1 ]; then
  echo ""
  echo "开始卸载底层驱动（macFUSE / ntfs-3g）..."
  if brew list ntfs-3g-mac &>/dev/null; then
    brew uninstall ntfs-3g-mac && echo "已卸载 ntfs-3g-mac"
  else
    echo "ntfs-3g-mac 未安装，跳过"
  fi
  if brew list --cask macfuse &>/dev/null; then
    brew uninstall --cask macfuse && echo "已卸载 macFUSE"
    echo "⚠️ macFUSE 内核扩展需重启一次才会完全卸除；如不再使用建议重启。"
  else
    echo "macfuse 未安装，跳过"
  fi
  echo "✅ 已完整卸载（含 macFUSE / ntfs-3g）。"
fi
