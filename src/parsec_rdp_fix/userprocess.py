"""Launch an installed application using its owner's ordinary Explorer token."""

import ctypes
import os
import subprocess
from ctypes import wintypes
from pathlib import Path

import psutil

from .engine import PatchError

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TOKEN_DUPLICATE = 0x0002
MAXIMUM_ALLOWED = 0x02000000
LOGON_WITH_PROFILE = 1


class StartupInfo(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("reserved", wintypes.LPWSTR),
        ("desktop", wintypes.LPWSTR),
        ("title", wintypes.LPWSTR),
        ("x", wintypes.DWORD),
        ("y", wintypes.DWORD),
        ("width", wintypes.DWORD),
        ("height", wintypes.DWORD),
        ("chars_x", wintypes.DWORD),
        ("chars_y", wintypes.DWORD),
        ("fill", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("show", wintypes.WORD),
        ("reserved_bytes", wintypes.WORD),
        ("reserved_buffer", ctypes.c_void_p),
        ("stdin", wintypes.HANDLE),
        ("stdout", wintypes.HANDLE),
        ("stderr", wintypes.HANDLE),
    ]


class ProcessInfo(ctypes.Structure):
    _fields_ = [
        ("process", wintypes.HANDLE),
        ("thread", wintypes.HANDLE),
        ("pid", wintypes.DWORD),
        ("tid", wintypes.DWORD),
    ]


class SidAttributes(ctypes.Structure):
    _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]


def _api():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)

    def define(dll, name, result, *argtypes):
        function = getattr(dll, name)
        function.restype = result
        function.argtypes = list(argtypes)
        return function

    handle = wintypes.HANDLE
    pointer = ctypes.POINTER
    return {
        "open_process": define(kernel, "OpenProcess", handle, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD),
        "close": define(kernel, "CloseHandle", wintypes.BOOL, handle),
        "session": define(
            kernel, "ProcessIdToSessionId", wintypes.BOOL, wintypes.DWORD, pointer(wintypes.DWORD)
        ),
        "open_token": define(
            security, "OpenProcessToken", wintypes.BOOL, handle, wintypes.DWORD, pointer(handle)
        ),
        "get_token": define(
            security,
            "GetTokenInformation",
            wintypes.BOOL,
            handle,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            pointer(wintypes.DWORD),
        ),
        "same_sid": define(security, "EqualSid", wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p),
        "sub_count": define(
            security, "GetSidSubAuthorityCount", ctypes.POINTER(ctypes.c_ubyte), ctypes.c_void_p
        ),
        "sub": define(
            security, "GetSidSubAuthority", pointer(wintypes.DWORD), ctypes.c_void_p, wintypes.DWORD
        ),
        "duplicate": define(
            security,
            "DuplicateTokenEx",
            wintypes.BOOL,
            handle,
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            pointer(handle),
        ),
        "create": define(
            security,
            "CreateProcessWithTokenW",
            wintypes.BOOL,
            handle,
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.LPCWSTR,
            pointer(StartupInfo),
            pointer(ProcessInfo),
        ),
    }


def _token_buffer(api, token, kind):
    size = wintypes.DWORD()
    api["get_token"](token, kind, None, 0, ctypes.byref(size))
    if not size.value:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_string_buffer(size.value)
    if not api["get_token"](token, kind, buffer, size.value, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer


def _sid(api, token):
    buffer = _token_buffer(api, token, 1)
    return buffer, ctypes.cast(buffer, ctypes.POINTER(SidAttributes)).contents.sid


def _medium_integrity(api, token):
    buffer = _token_buffer(api, token, 25)
    sid = ctypes.cast(buffer, ctypes.POINTER(SidAttributes)).contents.sid
    count = api["sub_count"](sid).contents.value
    integrity = api["sub"](sid, count - 1).contents.value
    return 0x1000 <= integrity < 0x3000


def _session(api, pid):
    value = wintypes.DWORD()
    if not api["session"](pid, ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    return value.value


def launch_regular_user(executable: Path, args: list[str] | None = None) -> int:
    """Requires an Explorer shell of the same account in this Windows session."""
    api = _api()
    close = api["close"]
    own_proc = api["open_process"](PROCESS_QUERY_LIMITED_INFORMATION, False, os.getpid())
    if not own_proc:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        own_token = wintypes.HANDLE()
        if not api["open_token"](own_proc, TOKEN_QUERY, ctypes.byref(own_token)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            own_record, own_sid = _sid(api, own_token)
            current_session = _session(api, os.getpid())
            for entry in psutil.process_iter(["pid", "name"]):
                if (entry.info["name"] or "").casefold() != "explorer.exe":
                    continue
                if _session(api, entry.pid) != current_session:
                    continue
                shell_proc = api["open_process"](PROCESS_QUERY_LIMITED_INFORMATION, False, entry.pid)
                if not shell_proc:
                    continue
                try:
                    shell_token = wintypes.HANDLE()
                    if not api["open_token"](
                        shell_proc, TOKEN_QUERY | TOKEN_DUPLICATE, ctypes.byref(shell_token)
                    ):
                        continue
                    try:
                        shell_record, shell_sid = _sid(api, shell_token)
                        if not api["same_sid"](own_sid, shell_sid) or not _medium_integrity(api, shell_token):
                            continue

                        primary = wintypes.HANDLE()
                        if not api["duplicate"](
                            shell_token, MAXIMUM_ALLOWED, None, 2, 1, ctypes.byref(primary)
                        ):
                            raise ctypes.WinError(ctypes.get_last_error())
                        try:
                            startup = StartupInfo()
                            startup.cb = ctypes.sizeof(StartupInfo)
                            info = ProcessInfo()
                            command = ctypes.create_unicode_buffer(
                                subprocess.list2cmdline([str(executable), *(args or [])])
                            )
                            if not api["create"](
                                primary,
                                LOGON_WITH_PROFILE,
                                str(executable),
                                command,
                                0,
                                None,
                                str(executable.parent),
                                ctypes.byref(startup),
                                ctypes.byref(info),
                            ):
                                raise ctypes.WinError(ctypes.get_last_error())
                            close(info.thread)
                            close(info.process)
                            return info.pid
                        finally:
                            close(primary)
                    finally:
                        close(shell_token)
                finally:
                    close(shell_proc)
        finally:
            close(own_token)
    finally:
        close(own_proc)
    raise PatchError("A regular-user Explorer session for this administrator account was not found.")
