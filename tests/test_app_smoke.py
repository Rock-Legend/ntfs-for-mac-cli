"""app.py headless 冒烟测试：TUI 能启动、渲染表格、正常退出（不触碰真实磁盘）。"""

import asyncio

from ntfs_tui.app import NTFSApp, main
from ntfs_tui.disks import NtfsVolume


def test_version_flag(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["ntfs-mate", "-v"])
    main()
    out = capsys.readouterr().out
    assert "ntfs-mate" in out
    assert "macFUSE" in out


def test_help_flag(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["ntfs-mate", "--help"])
    main()
    assert "用法" in capsys.readouterr().out


def test_unknown_arg_exits_2(monkeypatch, capsys):
    import pytest

    monkeypatch.setattr("sys.argv", ["ntfs-mate", "--bogus"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2
    assert "未知参数" in capsys.readouterr().err


def test_self_uninstall_removes_install(tmp_path):
    from ntfs_tui.app import self_uninstall

    app_dir = tmp_path / "opt" / "ntfs-mate"
    (app_dir / "venv" / "bin").mkdir(parents=True)
    (app_dir / "venv" / "bin" / "ntfs-mate").write_text("#!/bin/sh\n")
    bin_link = tmp_path / "bin" / "ntfs-mate"
    bin_link.parent.mkdir()
    bin_link.symlink_to(app_dir / "venv" / "bin" / "ntfs-mate")

    assert self_uninstall(app_dir, bin_link, confirm=lambda _p: "y") is True
    assert not app_dir.exists()
    assert not bin_link.exists()


def test_self_uninstall_abort_keeps_files(tmp_path):
    from ntfs_tui.app import self_uninstall

    app_dir = tmp_path / "opt" / "ntfs-mate"
    app_dir.mkdir(parents=True)
    bin_link = tmp_path / "bin" / "ntfs-mate"
    bin_link.parent.mkdir()
    bin_link.touch()

    assert self_uninstall(app_dir, bin_link, confirm=lambda _p: "n") is False
    assert app_dir.exists()
    assert bin_link.exists()

FAKE_VOLUMES = [
    NtfsVolume(
        device="/dev/disk4s1",
        volume_name="MyPassport",
        size_bytes=1_000_000_000_000,
        free_bytes=500_000_000_000,
        mount_point="/Volumes/MyPassport",
        writable=False,
        whole_disk="/dev/disk4",
    ),
    NtfsVolume(
        device="/dev/disk5s1",
        volume_name="未命名",
        size_bytes=500_000_000_000,
        free_bytes=0,
        mount_point="",
        writable=False,
        whole_disk="/dev/disk5",
    ),
]


def test_app_starts_and_renders(monkeypatch):
    monkeypatch.setattr("ntfs_tui.app.list_ntfs_volumes", lambda: FAKE_VOLUMES)
    monkeypatch.setattr(
        "ntfs_tui.app.check_deps",
        lambda: type("S", (), {"brew": True, "macfuse": True, "ntfs3g": True, "all_ok": True})(),
    )

    async def scenario():
        app = NTFSApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            # 等待 worker 完成一轮刷新
            for _ in range(50):
                await pilot.pause(0.1)
                if app.volumes:
                    break
            assert len(app.volumes) == 2
            assert app.selected_volume().volume_name == "MyPassport"
            app.exit()

    asyncio.run(scenario())
