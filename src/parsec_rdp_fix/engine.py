from __future__ import annotations

import ctypes
import json
import os
import subprocess
import time
import winreg
from dataclasses import dataclass
from pathlib import Path

import psutil

APP_NAME = "Parsec RDP Fix"
VERSION = "0.1.0"
SERVICE = "Parsec"
START_AUTOMATIC = 2
START_MANUAL = 3
START_DISABLED = 4
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Parsec.App.0"
STATE_KEY = r"Software\ParsecRDPFix"
SERVICE_REGISTRY = r"SYSTEM\CurrentControlSet\Services\Parsec"


class PatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class Snapshot:
    service_start: int
    service_running: bool
    run_value: str | None
    backup: dict | None
    installed: Path

    @property
    def patched(self) -> bool:
        return self.service_start == START_DISABLED and self.backup is not None


def _get_value(hive: int, path: str, name: str):
    try:
        with winreg.OpenKey(hive, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return None


def installed_path() -> Path:
    path = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Parsec" / "parsecd.exe"
    if not path.is_file():
        raise PatchError("Parsec was not found in Program Files.")

    profile = Path(os.environ["APPDATA"]) / "Parsec" / "config.json"
    if not profile.is_file():
        raise PatchError("Only per-user Parsec installations are supported.")

    binary = str(_get_value(winreg.HKEY_LOCAL_MACHINE, SERVICE_REGISTRY, "ImagePath") or "")
    if "pservice.exe" not in binary.casefold():
        raise PatchError("The Parsec service executable is not recognized.")

    return path


def get_start_type() -> int:
    value = _get_value(winreg.HKEY_LOCAL_MACHINE, SERVICE_REGISTRY, "Start")
    if value not in (START_AUTOMATIC, START_MANUAL, START_DISABLED):
        raise PatchError("Unexpected Parsec service startup type.")
    return int(value)


def is_admin() -> bool:
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def _read_backup() -> dict | None:
    raw = _get_value(winreg.HKEY_CURRENT_USER, STATE_KEY, "Backup")
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        if data["schema"] != 1 or data["start"] not in (START_AUTOMATIC, START_MANUAL):
            raise ValueError("unknown backup")
        if data["run"] is not None and not isinstance(data["run"], str):
            raise ValueError("unknown run command")
        return data
    except (ValueError, KeyError, TypeError) as exc:
        raise PatchError("The existing backup is invalid. No changes were made.") from exc


def _save_backup(data: dict) -> None:
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, STATE_KEY, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, "Backup", 0, winreg.REG_SZ, json.dumps(data))


def remove_backup() -> None:
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, STATE_KEY)
    except FileNotFoundError:
        pass


def _set_run(value: str | None) -> None:
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if value is None:
            try:
                winreg.DeleteValue(key, RUN_NAME)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, value)


def service_running() -> bool:
    return psutil.win_service_get(SERVICE).status() == "running"


def snapshot() -> Snapshot:
    path = installed_path()
    return Snapshot(
        service_start=get_start_type(),
        service_running=service_running(),
        run_value=_get_value(winreg.HKEY_CURRENT_USER, RUN_KEY, RUN_NAME),
        backup=_read_backup(),
        installed=path,
    )


def prepare_apply(state: Snapshot) -> None:
    if state.patched:
        raise PatchError("The fix is already applied.")
    if state.backup is not None or state.service_start == START_DISABLED:
        raise PatchError("A previous configuration is present. Restore it before proceeding.")

    if state.run_value and str(state.installed).casefold() not in state.run_value.casefold():
        raise PatchError("The Parsec startup entry points to another executable.")

    backup = {"schema": 1, "start": state.service_start, "run": state.run_value}
    _save_backup(backup)
    if state.run_value is None:
        _set_run(f'"{state.installed}" app_silent=1')


def revert_preparation() -> None:
    backup = _read_backup()
    if backup is None or get_start_type() != backup["start"]:
        return
    _set_run(backup["run"])
    remove_backup()


def finish_restore() -> None:
    backup = _read_backup()
    if backup is None:
        raise PatchError("No patch backup is available.")
    if get_start_type() != backup["start"]:
        raise PatchError("The service startup policy has not been restored.")
    _set_run(backup["run"])
    remove_backup()


def powershell_sc(*args: str) -> str:
    result = subprocess.run(
        ["sc.exe", *args],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise PatchError((result.stderr or result.stdout).strip() or "Could not change the Parsec service.")
    return result.stdout


def service_startup(start_type: int) -> None:
    types = {START_AUTOMATIC: "auto", START_MANUAL: "demand", START_DISABLED: "disabled"}
    powershell_sc("config", SERVICE, "start=", types[start_type])
    if get_start_type() != start_type:
        raise PatchError("Windows did not confirm the service startup change.")


def wait_service(running: bool, timeout: float = 18) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if service_running() == running:
            return
        time.sleep(0.3)
    raise PatchError("The Parsec service did not reach the expected state.")


def stop_service() -> None:
    if service_running():
        powershell_sc("stop", SERVICE)
        wait_service(False)


def start_service() -> None:
    if not service_running():
        powershell_sc("start", SERVICE)
        wait_service(True)


def parsec_processes() -> list[psutil.Process]:
    result = []
    for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "ppid"]):
        if (p.info["name"] or "").casefold() == "parsecd.exe":
            result.append(p)
    return result


def _safe_exe(p: psutil.Process) -> str:
    try:
        return (p.info.get("exe") or p.exe() or "").casefold()
    except (psutil.Error, OSError):
        return ""


def _process_session(pid: int) -> int:
    session = ctypes.c_ulong()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.ProcessIdToSessionId.argtypes = [ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    kernel.ProcessIdToSessionId.restype = ctypes.c_int
    if not kernel.ProcessIdToSessionId(pid, ctypes.byref(session)):
        raise ctypes.WinError(ctypes.get_last_error())
    return session.value


def close_installed_processes(exe: Path, service_pid: int | None) -> None:
    processes = parsec_processes()
    current_session = _process_session(os.getpid())
    installed = str(exe).casefold()
    candidates = set()
    for p in processes:
        cmd = " ".join(p.info.get("cmdline") or ())
        if (_safe_exe(p) == installed or "SERVICE_LAUNCHED_V13" in cmd) and (
            _process_session(p.pid) == current_session or p.info.get("ppid") == service_pid
        ):
            candidates.add(p.pid)
    for p in processes:
        if service_pid and p.info.get("ppid") == service_pid:
            candidates.add(p.pid)
        if p.pid in {p2.info.get("ppid") for p2 in processes if p2.pid in candidates}:
            candidates.add(p.pid)

    selected = [p for p in processes if p.pid in candidates]
    selected.sort(key=lambda p: p.info.get("ppid") not in candidates)
    for p in selected:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as exc:
            raise PatchError("Insufficient permission to stop a previous Parsec process.") from exc

    _, alive = psutil.wait_procs(selected, timeout=5)
    if alive:
        raise PatchError("A Parsec process is still running.")

    for p in parsec_processes():
        if _process_session(p.pid) == current_session and (
            _safe_exe(p) == installed or "SERVICE_LAUNCHED_V13" in " ".join(p.info.get("cmdline") or ())
        ):
            raise PatchError("A previous service-launched Parsec process is still active.")


def service_pid() -> int | None:
    service = psutil.win_service_get(SERVICE)
    return service.pid() or None


def usermode_ready(exe: Path) -> bool:
    matching = [p for p in parsec_processes() if _safe_exe(p) == str(exe).casefold()]
    if not matching:
        return False
    for p in matching:
        if "SERVICE_LAUNCHED_V13" in " ".join(p.info.get("cmdline") or ()):
            return False
    return True


def run_normal(exe: Path) -> int:
    from .userprocess import launch_regular_user

    return launch_regular_user(exe)
