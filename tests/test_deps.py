"""deps.py 单元测试：依赖检测（注入 which/path_exists，不触碰真实系统）。"""

from ntfs_tui.deps import check_deps


def _which_factory(found):
    return lambda cmd: f"/usr/local/bin/{cmd}" if cmd in found else None


def test_all_present():
    st = check_deps(
        which=_which_factory({"brew", "ntfs-3g"}),
        path_exists=lambda p: p == "/Library/Filesystems/macfuse.fs",
    )
    assert st.brew and st.macfuse and st.ntfs3g
    assert st.all_ok is True


def test_missing_ntfs3g():
    st = check_deps(
        which=_which_factory({"brew"}),
        path_exists=lambda p: True,
    )
    assert st.brew and st.macfuse and not st.ntfs3g
    assert st.all_ok is False


def test_nothing_present():
    st = check_deps(which=_which_factory(set()), path_exists=lambda p: False)
    assert not (st.brew or st.macfuse or st.ntfs3g)
    assert st.all_ok is False
