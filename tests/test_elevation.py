"""Non-disruptive checks for the regular-user Windows process launcher."""

import ctypes
from pathlib import Path

from parsec_rdp_fix import engine, userprocess


def test_startup_structure_has_windows_size():
    assert ctypes.sizeof(userprocess.StartupInfo) >= 68
    assert ctypes.sizeof(userprocess.ProcessInfo) >= 16


def test_installed_host_launch_uses_the_user_token(monkeypatch):
    calls = []
    monkeypatch.setattr(
        userprocess, "launch_regular_user", lambda executable: calls.append(executable) or 2468
    )
    executable = Path("C:/Program Files/Parsec/parsecd.exe")
    assert engine.run_normal(executable) == 2468
    assert calls == [executable]


def test_windows_process_token_types():
    assert userprocess.PROCESS_QUERY_LIMITED_INFORMATION == 0x1000
    assert userprocess.TOKEN_QUERY == 0x0008
    assert userprocess.LOGON_WITH_PROFILE == 1
