# NTFS Mate —— 项目架构图

> macOS 上的 NTFS 磁盘读写 / 可视化终端工具（TUI）。
> 本文档描述系统分层、模块职责、安装路径与运行时数据流，供维护与二次开发参考。

---

## 1. 目录结构

```
ntfs-for-mac-cli/
├── ntfs-mate            # 开发启动入口（指向源码 .venv，非安装产物）
├── install.sh           # 一键安装脚本（网络稳健：自动探测代理 + 重试）
├── pyproject.toml       # 打包定义（版本单一数据源 / console_scripts / 测试配置）
├── Formula/
│   └── ntfs-mate.rb     # Homebrew formula（brew install 一条命令装全）
├── src/ntfs_tui/        # 应用源码
│   ├── __main__.py      # 入口：调用 app.main()
│   ├── app.py           # TUI 主程序（界面布局 + Textual CSS 样式 + 交互逻辑）
│   ├── disks.py         # 磁盘探测（diskutil / 卷名 / 设备 / 挂载状态）
│   ├── mounter.py       # 挂载 / 卸载（sudo + ntfs-3g，含脏标记/休眠引导）
│   └── deps.py          # 依赖检查（macFUSE / ntfs-3g / 版本）
├── tests/               # 35 个 pytest 用例（deps / disks / mounter / app smoke）
├── docs/superpowers/    # 设计稿与实现计划（specs / plans）
├── README.md            # 使用说明
├── CHANGELOG.md         # 语义化版本变更记录
└── LICENSE              # 开源协议
```

> `.venv/`（运行时虚拟环境）与 `build/`（构建产物）已被 `.gitignore` 忽略，不入库。

---

## 2. 系统分层架构

```mermaid
flowchart TB
    subgraph U["用户层"]
        USER["终端用户（macOS）"]
        FINDER["访达（Finder）"]
    end

    subgraph TUI["TUI 层 —— src/ntfs_tui/app.py"]
        APP["NTFSApp 主界面"]
        TABLE["DataTable 磁盘列表"]
        DIALOG["PasswordScreen / MessageScreen 弹窗"]
        FOOTER["Footer 快捷键提示"]
    end

    subgraph BIZ["业务层 —— src/ntfs_tui"]
        DISKS["disks.py\n磁盘探测"]
        MOUNTER["mounter.py\n挂载 / 卸载"]
        DEPS["deps.py\n依赖检查"]
    end

    subgraph SYS["macOS 系统层"]
        DISKUTIL["diskutil"]
        SUDO["sudo 提权"]
        VOLUMES["/Volumes 挂载点"]
    end

    subgraph EXT["外部驱动依赖"]
        FUSE["macFUSE 内核扩展"]
        NTFS3G["ntfs-3g-mac\n读写驱动"]
    end

    USER --> APP
    APP --> TABLE
    APP --> DIALOG
    APP --> FOOTER
    APP --> DISKS
    APP --> MOUNTER
    APP --> DEPS

    DISKS --> DISKUTIL
    MOUNTER --> SUDO
    MOUNTER --> VOLUMES
    SUDO --> NTFS3G
    NTFS3G --> FUSE
    MOUNTER --> FINDER
    FINDER --> VOLUMES
```

---

## 3. 模块依赖关系

```mermaid
flowchart LR
    MAIN["__main__.py"] --> APP["app.py"]
    APP --> DISKS["disks.py"]
    APP --> MOUNTER["mounter.py"]
    APP --> DEPS["deps.py"]
    MOUNTER --> DISKS
    DEPS -->|调用| DISKUTIL[("diskutil\n/tap 状态")]

    style MAIN fill:#1e293b,stroke:#00f0ff,color:#e2e8f0
    style APP fill:#1e293b,stroke:#00f0ff,color:#e2e8f0
    style DISKS fill:#1e293b,stroke:#bf5af2,color:#e2e8f0
    style MOUNTER fill:#1e293b,stroke:#bf5af2,color:#e2e8f0
    style DEPS fill:#1e293b,stroke:#bf5af2,color:#e2e8f0
```

| 模块 | 职责 | 依赖 |
|---|---|---|
| `__main__.py` | 程序入口，调用 `app.main()` | app |
| `app.py` | TUI 主界面、表格、弹窗、快捷键、全部交互逻辑与样式 | disks / mounter / deps |
| `disks.py` | 通过 `diskutil` 探测 NTFS 磁盘、卷名、设备路径、挂载状态 | 系统 diskutil |
| `mounter.py` | 以 `sudo` 调用 `ntfs-3g` 完成挂载/卸载；处理脏标记、Windows 休眠引导；`/Volumes` 建点 sudo 兜底 | disks / sudo / ntfs-3g |
| `deps.py` | 校验 macFUSE、ntfs-3g 是否就绪并给出中文修复建议 | diskutil / brew |

---

## 4. 安装 / 部署架构（两条路径）

```mermaid
flowchart TD
    START["开始安装"] --> CHOOSE{"选择安装方式"}

    CHOOSE -->|方式 A：脚本| SCRIPT["./install.sh"]
    CHOOSE -->|方式 B：Homebrew| BREW["brew install ntfs-mate"]

    subgraph A["方式 A —— install.sh"]
        S1["探测本机代理端口\n设 HOMEBREW_HTTPS_PROXY 等"]
        S2["brew install --cask macfuse"]
        S3["brew install gromgit/fuse/ntfs-3g-mac\n（失败自动重试退避）"]
        S4["构建 wheel → 独立 venv\n装入 $(brew --prefix)/opt/ntfs-mate"]
        S5["软链全局命令 → $(brew --prefix)/bin/ntfs-mate"]
        S1 --> S2 --> S3 --> S4 --> S5
    end

    subgraph B["方式 B —— Homebrew formula"]
        B1["Formula 自动 depends_on"]
        B2["macFUSE（cask）"]
        B3["gromgit/fuse/ntfs-3g-mac（formula）"]
        B4["python@3.13 + venv 安装本包"]
        B1 --> B2 --> B3 --> B4
    end

    SCRIPT --> A
    BREW --> B

    A --> EXT["外部驱动依赖\n（始终来自 GitHub：gromgit tap）"]
    B --> EXT
    EXT --> DONE["安装完成：源码目录可删除"]

    style A fill:#0f172a,stroke:#00f0ff,color:#e2e8f0
    style B fill:#0f172a,stroke:#00f0ff,color:#e2e8f0
```

**关键说明**

- 方式 A 与方式 B 最终都把应用装入 `$(brew --prefix)/opt/ntfs-mate` 并注册全局命令，**源码目录可整体删除**。
- macFUSE 与 ntfs-3g 这两个真正"卡网络"的驱动**始终来自 GitHub**（gromgit tap），因此最终用户安装驱动仍需代理；`install.sh` 已内置代理自动探测，formula 在 caveats 中提示配置代理。
- 源码可托管于任意 git 平台（GitHub / Gitee / 自建），仅影响自家代码下载速度，不改变驱动来源。

---

## 5. 运行时挂载数据流（时序）

```mermaid
sequenceDiagram
    participant U as 用户
    participant APP as NTFSApp
    participant M as mounter.py
    participant S as sudo
    participant N as ntfs-3g
    participant F as 访达

    U->>APP: 选中磁盘，按 M（读写挂载）
    APP->>APP: 弹出 PasswordScreen
    U->>APP: 输入开机密码
    APP->>M: mount(device, rw, password)
    M->>M: 确保 /Volumes 挂载点\n（无权限则 sudo 兜底）
    M->>S: sudo mount_ntfs / ntfs-3g -o rw
    S->>N: 加载 ntfs-3g 读写驱动
    N->>N: 检测脏标记 / 休眠
    alt 脏标记或 Windows 休眠
        N-->>M: 报错
        M-->>APP: 返回中文引导（建议先安全弹出 / chkdsk）
        APP-->>U: MessageScreen 提示
    else 正常
        N-->>S: 挂载成功
        S-->>M: 返回 0
        M-->>APP: 成功
        APP->>F: 触发访达显示卷
        APP-->>U: 状态更新（已挂载 / 读写）
    end
```

---

## 6. 外部依赖一览

| 依赖 | 类型 | 来源 | 作用 |
|---|---|---|---|
| `macFUSE` | Homebrew cask | GitHub `macFUSE/macFUSE` | NTFS 内核扩展框架（首次需系统设置授权） |
| `ntfs-3g-mac` | Homebrew formula | `gromgit/fuse` tap（GitHub / ghcr.io） | 实际的 NTFS 读写驱动 |
| `python@3.13` | Homebrew formula | Homebrew core | 运行 TUI（Textual 8.x） |
| `Textual` | PyPI 包 | PyPI（pip） | TUI 框架 |

---

## 7. 版本与状态

- 当前版本：**0.3.0**（语义化版本，单一数据源在 `pyproject.toml`）。
- 入口命令：`ntfs-mate`（全局）、`ntfs-mate -v`（版本）、`ntfs-mate -h`（帮助）。
- 测试：35 个 pytest 用例全绿，覆盖 deps / disks / mounter / app 冒烟。
- 版本基线：**v0.3.0**（遵循语义化版本，后续发布按 `vX.Y.Z` 打 tag；标签历史自本次托管重新起算，不再保留 v0.2.x 旧标签）。
