"""NTFS Mate — macOS NTFS 读写 TUI 工具。"""

# 版本号单一数据源在 pyproject.toml / dist-info，运行时从元数据读取，避免写死导致不一致。
try:
    from importlib.metadata import version as _metadata_version

    __version__ = _metadata_version("ntfs-mate")
except Exception:
    __version__ = "0.0.0-dev"
