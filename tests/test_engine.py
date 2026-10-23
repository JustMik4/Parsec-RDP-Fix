"""Service ordering and restoration tests; no live Windows services are touched."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from parsec_rdp_fix import engine, worker


@pytest.fixture
def setup_system(monkeypatch, tmp_path):
    exe = tmp_path / "parsecd.exe"
    exe.write_text("test-only")
    calls = []
    state = {"start": 2, "running": True, "user": False, "backup": None}

    def snapshot():
        return engine.Snapshot(state["start"], state["running"], '"parsecd.exe"', state["backup"], exe)

    def prepare(original):
        calls.append("prepare")
        state["backup"] = {"schema": 1, "start": original.service_start, "run": original.run_value}

    def start_type(value):
        calls.append(("startup", value))
        state["start"] = value

    def stop():
        calls.append("stop")
        state["running"] = False

    def start():
        calls.append("start")
        state["running"] = True

    def close(_exe, pid):
        calls.append(("close", pid))
        state["user"] = False

    def launch(_exe):
        calls.append("regular_launch")
        state["user"] = True

    monkeypatch.setattr(engine, "is_admin", lambda: True)
    monkeypatch.setattr(engine, "snapshot", snapshot)
    monkeypatch.setattr(engine, "prepare_apply", prepare)
    monkeypatch.setattr(engine, "service_startup", start_type)
    monkeypatch.setattr(engine, "stop_service", stop)
    monkeypatch.setattr(engine, "start_service", start)
    monkeypatch.setattr(engine, "close_installed_processes", close)
    monkeypatch.setattr(engine, "service_pid", lambda: 94)
    monkeypatch.setattr(engine, "run_normal", launch)
    monkeypatch.setattr(engine, "usermode_ready", lambda _exe: state["user"])
    monkeypatch.setattr(engine, "service_running", lambda: state["running"])
    monkeypatch.setattr(engine, "revert_preparation", lambda: calls.append("undo_backup"))
    monkeypatch.setattr(engine, "finish_restore", lambda: calls.append("restore_backup"))
    monkeypatch.setattr(worker, "wait_for_user_host", lambda _exe, timeout=22: None)
    return state, calls, exe


def test_apply_starts_user_host_before_restarting_service(setup_system):
    state, calls, _ = setup_system
    events = []
    worker.apply(events.append)
    assert calls == [
        "prepare",
        "stop",
        ("close", 94),
        ("startup", engine.START_MANUAL),
        "regular_launch",
        "start",
        ("startup", engine.START_DISABLED),
    ]
    assert state["start"] == engine.START_DISABLED
    assert state["user"] is True
    assert events == ["stopping", "launch", "service", "done"]


def test_apply_restores_original_service_on_launch_error(setup_system, monkeypatch):
    state, calls, _ = setup_system

    def fail(_exe):
        raise engine.PatchError("Explorer token unavailable")

    monkeypatch.setattr(engine, "run_normal", fail)
    with pytest.raises(engine.PatchError, match="Explorer token unavailable"):
        worker.apply(lambda phase: None)

    assert state["start"] == engine.START_AUTOMATIC
    assert state["running"]
    assert "undo_backup" in calls


def test_apply_preserves_backup_when_recovery_incomplete(setup_system, monkeypatch):
    state, calls, _ = setup_system

    def fail(_exe):
        raise engine.PatchError("Cannot launch")

    def recovery_error(value):
        if value == 2:
            raise OSError("Service inaccessible")
        state["start"] = value

    monkeypatch.setattr(engine, "run_normal", fail)
    monkeypatch.setattr(engine, "service_startup", recovery_error)
    with pytest.raises(engine.PatchError, match="Recovery was incomplete"):
        worker.apply(lambda phase: None)
    assert "undo_backup" in calls


def test_restore_requires_original_backup(setup_system):
    with pytest.raises(engine.PatchError, match="No backup exists"):
        worker.restore(lambda phase: None)


def test_restore_restarts_original_service_and_host(setup_system):
    state, calls, _ = setup_system
    state["backup"] = {"schema": 1, "start": 2, "run": None}
    state["start"] = 4
    events = []
    worker.restore(events.append)
    assert calls == ["stop", ("close", 94), ("startup", 2), "start", "restore_backup", "regular_launch"]
    assert events == ["stopping", "service", "launch", "done"]


def test_admin_is_required_for_apply_and_restore(setup_system, monkeypatch):
    monkeypatch.setattr(engine, "is_admin", lambda: False)
    with pytest.raises(engine.PatchError, match="Administrator privileges"):
        worker.apply(lambda x: None)
    with pytest.raises(engine.PatchError, match="Administrator privileges"):
        worker.restore(lambda x: None)


def test_backup_idempotency():
    state = engine.Snapshot(4, False, None, {"schema": 1, "start": 2, "run": None}, Path("parsecd.exe"))
    assert state.patched


def test_user_mode_launch_delegates_to_shell_token(monkeypatch):
    from parsec_rdp_fix import userprocess

    invoked = []
    monkeypatch.setattr(userprocess, "launch_regular_user", lambda exe: invoked.append(exe) or 121)
    exe = Path("C:/Program Files/Parsec/parsecd.exe")
    assert engine.run_normal(exe) == 121
    assert invoked == [exe]


def test_process_cleanup_preserves_other_user_sessions(monkeypatch):
    class FakeProcess:
        def __init__(self, pid, parent, session):
            self.pid = pid
            self.info = {
                "name": "parsecd.exe",
                "exe": "C:\\Program Files\\Parsec\\parsecd.exe",
                "cmdline": ["parsecd.exe"],
                "ppid": parent,
            }
            self.session = session
            self.killed = False

        def kill(self):
            self.killed = True

    owner = FakeProcess(510, 10, 1)
    remote = FakeProcess(511, 10, 4)
    processes = [owner, remote]
    monkeypatch.setattr(engine, "parsec_processes", lambda: [p for p in processes if not p.killed])
    monkeypatch.setattr(engine, "_process_session", lambda pid: {510: 1, 511: 4, 100: 1}[pid])
    monkeypatch.setattr(engine.os, "getpid", lambda: 100)
    monkeypatch.setattr(engine.psutil, "wait_procs", lambda selected, timeout: (selected, []))

    engine.close_installed_processes(Path("C:\\Program Files\\Parsec\\parsecd.exe"), None)
    assert owner.killed
    assert not remote.killed


def test_service_startup_rejects_unknown_type():
    with pytest.raises(KeyError):
        engine.service_startup(99)


def test_prepare_rejects_unknown_run_entry(monkeypatch):
    state = engine.Snapshot(
        2, True, "C:/Other/Application.exe", None, Path("C:/Program Files/Parsec/parsecd.exe")
    )
    monkeypatch.setattr(engine, "_save_backup", Mock())
    with pytest.raises(engine.PatchError, match="another executable"):
        engine.prepare_apply(state)
