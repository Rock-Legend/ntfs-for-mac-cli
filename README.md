# NTFS Mate

macOS 上的 NTFS 硬盘读写工具 — 终端可视化（TUI）界面，让 NTFS 硬盘在访达中正常读、写、删除、挂载、弹出。

![macOS](https://img.shields.io/badge/macOS-Intel%20%7C%20Apple%20Silicon-blue)

## 功能

- **可视化磁盘列表**：卷名、设备、总容量/可用空间、挂载状态（未挂载/只读/读写）、挂载点，每 3 秒自动刷新（热插拔即时可见）
- **一键读写挂载**：基于 macFUSE + ntfs-3g，挂载后在访达中正常读、写、删除
- **只读挂载 / 卸载 / 弹出整盘 / 访达打开**
- **智能错误引导**：Windows 休眠、NTFS 脏标记等常见问题给出中文处理建议
- **一键安装**：`install.sh` 自动装齐全部依赖（含代理自适应与重试）
- **Homebrew 安装**：支持 `brew install ntfs-mate`，一条命令装全

## 安装

### 方式一：Homebrew（推荐，一条命令装全）

```bash
# 本仓库已自带 Formula，可直接本地安装：
brew install --formula ./Formula/ntfs-mate.rb

# 或作为 tap 安装（先 tap 本仓库）：
brew tap jonegao/ntfs-for-mac-cli
brew install ntfs-mate
```

formula 会自动拉取 macFUSE（cask）与 `gromgit/fuse/ntfs-3g-mac`，并把 `ntfs-mate` 注册到 `$(brew --prefix)/bin`。

### 方式二：安装脚本

```bash
./install.sh
```

标准 CLI 安装（遵循 Homebrew 目录惯例），脚本自动完成：

1. `brew install --cask macfuse`（NTFS 内核驱动框架）
2. `brew install gromgit/fuse/ntfs-3g-mac`（NTFS 读写驱动）
3. 从源码构建 wheel，装入独立运行环境 `$(brew --prefix)/opt/ntfs-mate/`
4. 注册全局命令 `$(brew --prefix)/bin/ntfs-mate`

**安装完成后本源码目录即可删除**，应用与源码完全无关。

> ⚠️ **首次使用 macFUSE 需要授权内核扩展**：
> 系统设置 → 隐私与安全性 → 允许 "macFUSE"（Benjamin Fleischer），按提示重启一次（仅首次）。
>
> Apple Silicon 机型还需先在恢复模式中允许第三方内核扩展（降低安全策略一次）。

> 🌐 **GitHub 网络超时（国内常见）**：macFUSE / ntfs-3g 的下载与编译都来自 GitHub / tuxera / ghcr.io，直连极易超时。请先为 brew 配置代理再安装：
> ```bash
> export HOMEBREW_HTTPS_PROXY=http://127.0.0.1:7897
> export HOMEBREW_HTTP_PROXY=http://127.0.0.1:7897
> ```
> `./install.sh` 会自动探测本机代理端口（Clash/Surge 等）并仅为本次安装启用，无需手动设置。

## 卸载

```bash
ntfs-mate uninstall
```

交互确认后移除全局命令与应用本体（`$(brew --prefix)/opt/ntfs-mate`），保留 macFUSE/ntfs-3g 驱动。源码目录还在的话也可运行 `./uninstall.sh`。

## 使用

终端**任意目录**直接运行：

```bash
ntfs-mate
```

| 快捷键 | 动作 |
|---|---|
| `M` | 挂载为读写（需输入开机密码一次，挂载后访达可读/写/删除） |
| `R` | 只读挂载（macOS 原生，无需密码） |
| `U` | 卸载 |
| `E` | 弹出整盘（可安全拔出） |
| `O` | 在访达中打开 |
| `D` | 依赖状态 / 安装引导 |
| `F5` | 手动刷新 |
| `Q` | 退出 |

↑↓ 或鼠标选择磁盘。

## 常见问题

- **挂载失败提示「Windows 休眠文件」**：在 Windows 中彻底关机（设置 → 电源 → 关闭「快速启动」）后重试。
- **提示「NTFS 日志未正常关闭」**：上次未安全弹出，在 Windows 中运行 `chkdsk /f` 修复后重试。
- **挂载后访达看不到盘**：确认已允许 macFUSE 内核扩展（见上方安装说明）。

## 真机验证清单

1. 插入 NTFS 移动硬盘 → 列表 3 秒内出现，状态显示「只读」（macOS 默认）
2. 选中按 `M` → 输入开机密码 → 状态变为「读写」
3. 按 `O` 打开访达 → 新建文件夹、拷入文件、删除文件均正常
4. 按 `U` 卸载 → 访达中消失；按 `E` 弹出 → 整盘断电可拔出

## 开发

```bash
# 开发环境（可编辑安装 + 测试依赖）
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 运行测试（不触碰真实磁盘，全部 mock）
.venv/bin/pytest -v
```

版本发布规范：版本号只改 `pyproject.toml`，提交后打 `git tag v<x.y.z>`，并在 CHANGELOG.md 记录。

项目结构：

```
pyproject.toml      打包定义（版本/依赖/console_scripts/pytest 配置，单一数据源）
Formula/ntfs-mate.rb Homebrew formula（brew install 一条命令装全）
install.sh          一键安装到系统标准位置（原子替换，失败不留半成品，代理自适应+重试）
uninstall.sh        卸载（与 ntfs-mate uninstall 等效）
ntfs-mate           开发期启动入口（项目内 .venv）
LICENSE / CHANGELOG.md
src/ntfs_tui/
  ├── app.py        Textual TUI 主界面 + CLI 入口（-v/-h/uninstall）
  ├── disks.py      磁盘探测（diskutil plist 解析）
  ├── mounter.py    挂载/卸载/弹出 + 错误引导
  └── deps.py       依赖检测
tests/              单元测试 + TUI headless 冒烟
docs/               设计文档与实现计划
```

## 已知限制

- ntfs-3g 为 FUSE 用户态驱动，大文件连续读写性能低于原生或商业驱动（Paragon/Tuxera）
- Apple Silicon 需一次性降低安全策略以加载 macFUSE kext
- 开启 Windows「快速启动」或处于休眠状态的盘需先处理（工具内会给出引导）
