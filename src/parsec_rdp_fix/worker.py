"""Manage Parsec service startup while keeping its host in regular user mode."""

from __future__ import annotations

import time
from collections.abc import Callable

from . import engine

Progress = Callable[[str], None]


def wait_for_user_host(executable, timeout: float = 22) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if engine.usermode_ready(executable):
            return
        time.sleep(0.4)
    raise engine.PatchError("Parsec did not start as a regular user.")


def apply(progress: Progress) -> None:
    if not engine.is_admin():
        raise engine.PatchError("Administrator privileges are required to apply this fix.")

    state = engine.snapshot()
    engine.prepare_apply(state)

    try:
        progress("stopping")
        service_pid = engine.service_pid()
        engine.stop_service()
        engine.close_installed_processes(state.installed, service_pid)

        engine.service_startup(engine.START_MANUAL)
        progress("launch")
        engine.run_normal(state.installed)
        wait_for_user_host(state.installed)

        progress("service")
        engine.start_service()
        engine.service_startup(engine.START_DISABLED)
        if not engine.usermode_ready(state.installed):
            raise engine.PatchError("The service took over the regular-user Parsec host.")
        if not engine.service_running():
            raise engine.PatchError("The Parsec service failed to start.")

        progress("done")
    except Exception as error:
        failures = []
        try:
            engine.service_startup(state.service_start)
            engine.start_service()
        except Exception as recovery:
            failures.append(str(recovery))
        try:
            engine.revert_preparation()
        except Exception as recovery:
            failures.append(str(recovery))
        if failures:
            raise engine.PatchError(f"{error}\n\nRecovery was incomplete: {'; '.join(failures)}") from error
        raise


def restore(progress: Progress) -> None:
    if not engine.is_admin():
        raise engine.PatchError("Administrator privileges are required to restore Parsec.")

    state = engine.snapshot()
    backup = state.backup
    if backup is None:
        raise engine.PatchError("No backup exists. There is nothing to restore.")

    try:
        progress("stopping")
        service_pid = engine.service_pid()
        engine.stop_service()
        engine.close_installed_processes(state.installed, service_pid)

        progress("service")
        engine.service_startup(backup["start"])
        engine.start_service()
        engine.finish_restore()
        progress("launch")
        engine.run_normal(state.installed)
        progress("done")
    except Exception:
        try:
            engine.service_startup(backup["start"])
            engine.start_service()
        except (OSError, engine.PatchError):
            pass
        raise
