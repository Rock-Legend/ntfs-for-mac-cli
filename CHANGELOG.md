# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.3.0] - 2026-08-09

### 新增
- 提供 Homebrew formula（`Formula/ntfs-mate.rb`），支持 `brew install ntfs-mate`（或本地 `brew install --formula ./Formula/ntfs-mate.rb`）一条命令装全，自动拉取 macFUSE cask 与 `gromgit/fuse/ntfs-3g-mac`，并把命令注册到 `$(brew --prefix)/bin`。
- 项目托管到 GitHub `Rock-Legend/ntfs-for-mac-cli`：formula 的 `homepage` / `url` 及 README 的 tap 命令全部迁移到该地址；公式直接放在主仓库 `Formula/` 目录，无需单独的 `homebrew-*` 仓库。
- 新增发版脚本 `scripts/release-formula.sh`：打 tag 并 push 后一键下载 GitHub tarball、计算 sha256 并写回 `Formula/ntfs-mate.rb`，自动提交推送，闭合 brew 安装的最后一步（占位 sha 必须回填才能 `brew install`）。
- `install.sh` 新增代理自适应：自动探测本机代理端口（Clash/Surge 等）并仅为本次安装启用；同时设置 `HOMEBREW_HTTPS_PROXY` / `HOMEBREW_HTTP_PROXY` / `https_proxy`，让 brew、git clone tap、curl 全部真正走代理（此前 brew 默认不读 `https_proxy`，是 GitHub 超时的根因）。
- `install.sh` 的 `brew tap` / `brew install` 增加重试退避（最多 4 次），应对偶发网络抖动。

### 修正
- macFUSE 继续走官方 cask（gromgit 无 macfuse formula），并以 `/usr/local/include/fuse.h` 作为安装完整性硬校验；仍缺失时打开 pkg 兜底并给出内核扩展批准指引，不再"只装一半"。
- 移除无效的 USTC mirror 兜底分支（gromgit 的 ghcr bottle 不在 USTC 镜像范围内，反而在 unset 代理后加重失败），统一依赖代理路径。
- README 增加「托管与发版」小节，给出完整发布流程。

## [0.2.6] - 2026-08-09

### 改进
- 主界面表格区去掉厚重外边框，改为仅保留上下两条细线分隔，减少空框感。
- 表头背景透明化并与表格背景融为一体，不再出现深色"色块"。
- 关闭斑马纹，多行时依赖光标/悬停高亮区分，整体更简洁。

## [0.2.5] - 2026-08-09

### 改进
- 弹框重新设计为紧凑卡片风格：去掉厚重 `tall` 边框，改用单色细线 `solid` 边框；标题/内容/按钮垂直紧凑排列，减少空行；按钮改为更小的居中按钮。
- MessageScreen 支持 `severity` 参数（info/success/warning/error），不同状态使用对应霓虹边框和标题色。
- 密码弹框移除 emoji 图标（避免终端宽度渲染不一致），以紫色霓虹标题替代。

## [0.2.4] - 2026-08-09

### 修正
- Footer 快捷键仍不显示：给 Footer 加的 `border-top` 独占了其仅有的 1 行高度，把内部快捷键文字挤没。移除 Footer 边框，保留背景色区分，快捷键恢复正常。

## [0.2.3] - 2026-08-09

### 修正
- Footer 快捷键被隐藏：Textual 8.x 的 Footer 子组件类名为 `FooterKey` / `FooterLabel`，不是旧版 `.footer--key` / `.footer--description`。修复后底部快捷键重新显示。

## [0.2.2] - 2026-08-09

### 改进
- UI 全面科技化：密码弹框、消息弹框、通知（notify）统一加入霓虹青/紫/红边框、图标、渐变文字、发光聚焦效果
- PasswordScreen 增加 🔒 图标与副标题说明，按钮改为居中布局
- MessageScreen 根据错误/信息类型显示不同图标与边框颜色
- 通知使用彩色左侧边条，成功/警告/错误一目了然

## [0.2.1] - 2026-08-09

### 修正
- **真机挂载失败**：/Volumes 属 root:wheel，普通用户创建挂载点报 PermissionError(13)；现在自动用 sudo 补建（复用挂载密码）
- TUI 异常兜底：挂载/卸载/刷新任一路径抛出非 MountError 异常时弹错误框，不再让整个程序崩溃退出
- install.sh：`yes | brew install` 刷屏且因 pipefail+SIGPIPE 误报安装失败，改为有限预答 + 退出码保真
- install.sh：变量后紧跟中文标点在 bash 3.2 下被并入变量名（set -u 报错），全部加花括号
- install.sh：GitHub 访问自动探测本机代理；bottle 下载失败自动切 USTC 镜像直连；macFUSE 以 fuse.h 为准校验完整性

## [0.2.0] - 2026-08-09

### 新增
- `ntfs-mate uninstall` 自卸载子命令（无需源码目录，交互确认后移除全局命令与应用本体）
- `ntfs-mate -h/--help` 用法说明
- LICENSE（MIT）、CHANGELOG

### 修正
- 未知参数不再静默启动 TUI：报错到 stderr 并以退出码 2 结束（CLI 惯例）
- 依赖缺失提示改为直接给出 brew 命令，不再假定源码目录存在
- install.sh 升级保护：旧版本先备份，构建失败自动回滚（venv 原地构建，保证 shebang 正确）
- install.sh 前置检查 Python ≥ 3.9

### 工程
- pyproject.toml 补全 keywords/classifiers，license 改用 PEP 639 标准写法
- 开发依赖统一为 `pip install -e ".[dev]"`，删除重复的 requirements.txt
- pytest 配置内置于 pyproject（免设 PYTHONPATH）
- 版本号规范：pyproject.toml 为唯一数据源 + git tag

## [0.1.1] - 2026-08-09

### 新增
- `ntfs-mate -v/--version`：版本号 + macFUSE/ntfs-3g/brew 驱动状态

## [0.1.0] - 2026-08-09

### 新增
- 首个可用版本：NTFS 磁盘可视化列表（3 秒自动刷新）、读写/只读挂载、卸载、弹出、访达打开、中文错误引导
- 标准 CLI 安装：构建 wheel 装入 `$(brew --prefix)/opt/ntfs-mate/`，全局命令注册到 `$(brew --prefix)/bin/`，附 uninstall.sh，装完源码目录可删除
