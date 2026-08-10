"""依赖检测：brew / macFUSE / ntfs-3g。"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

MACFUSE_PATH = "/Library/Filesystems/macfuse.fs"


@dataclass
class DepStatus:
    brew: bool
    macfuse: bool
    ntfs3g: bool

    @property
    def all_ok(self) -> bool:
        return self.brew and self.macfuse and self.ntfs3g


def check_deps(which=shutil.which, path_exists=os.path.exists) -> DepStatus:
    """检测三类依赖是否就绪。注入 which/path_exists 便于测试。"""
    return DepStatus(
        brew=which("brew") is not None,
        macfuse=bool(path_exists(MACFUSE_PATH)),
        ntfs3g=which("ntfs-3g") is not None,
    )
