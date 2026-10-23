"""Interface and locale behavior, without touching Parsec services."""

import queue
from types import SimpleNamespace

from parsec_rdp_fix import engine, i18n, worker
from parsec_rdp_fix.i18n import LANGUAGES, Translator
from parsec_rdp_fix.ui import FixWindow


def test_all_translations():
    expected = set(Translator("en").fallback)
    for lang in LANGUAGES:
        entries = Translator(lang).catalog
        assert set(entries) == expected
        assert all(value.strip() for value in entries.values())


def _dummy_ui(monkeypatch, admin=True):
    monkeypatch.setattr(engine, "is_admin", lambda: admin)
    actions = []
    ui = SimpleNamespace(
        t=lambda key: key,
        _begin=lambda action: actions.append(action),
        operation=None,
    )
    return ui, actions


def test_administrator_can_apply(monkeypatch):
    ui, actions = _dummy_ui(monkeypatch, True)
    monkeypatch.setattr("parsec_rdp_fix.ui.messagebox.askyesno", lambda *args, **kwargs: True)
    FixWindow._apply(ui)
    assert actions == ["apply"]


def test_administrator_can_restore(monkeypatch):
    ui, actions = _dummy_ui(monkeypatch, True)
    monkeypatch.setattr("parsec_rdp_fix.ui.messagebox.askyesno", lambda *args, **kwargs: True)
    FixWindow._restore(ui)
    assert actions == ["restore"]


def test_restore_denied_without_administrator(monkeypatch):
    ui, actions = _dummy_ui(monkeypatch, False)
    messages = []
    monkeypatch.setattr(
        "parsec_rdp_fix.ui.messagebox.showerror", lambda *args, **kwargs: messages.append(args)
    )
    FixWindow._restore(ui)
    assert actions == []
    assert messages


def test_apply_denied_without_administrator(monkeypatch):
    ui, actions = _dummy_ui(monkeypatch, False)
    monkeypatch.setattr("parsec_rdp_fix.ui.messagebox.showerror", lambda *args, **kwargs: None)
    FixWindow._apply(ui)
    assert actions == []


def test_background_progress_and_completion():
    messages = []
    fake = SimpleNamespace(
        events=queue.SimpleQueue(),
        _show_message=lambda value: messages.append(value),
        _finish=lambda kind, detail: messages.append((kind, detail)),
        after=lambda *args: None,
        _poll=lambda: None,
    )
    fake.events.put(("progress", "stopping"))
    fake.events.put(("done", ""))
    FixWindow._poll(fake)
    assert messages == ["progress_stopping", ("done", "")]


def test_background_failure_is_reported(monkeypatch):
    def fail(progress):
        raise OSError("Synthetic worker error")

    monkeypatch.setattr(worker, "apply", fail)
    fake = SimpleNamespace(events=queue.SimpleQueue())
    FixWindow._execute(fake, "apply")
    assert fake.events.get_nowait() == ("error", "Synthetic worker error")


def test_windows_language_selection(monkeypatch):
    monkeypatch.setattr(i18n.sys, "platform", "win32")
    for langid, expected in (
        (0x0416, "pt"),
        (0x0409, "en"),
        (0x080A, "es"),
        (0x0419, "ru"),
        (0x0804, "zh"),
        (0x0411, "ja"),
    ):
        monkeypatch.setattr(
            i18n.ctypes,
            "windll",
            SimpleNamespace(kernel32=SimpleNamespace(GetUserDefaultUILanguage=lambda langid=langid: langid)),
            raising=False,
        )
        assert i18n.system_language() == expected


def test_unknown_windows_language_uses_english(monkeypatch):
    monkeypatch.setattr(i18n.sys, "platform", "win32")
    monkeypatch.setattr(
        i18n.ctypes,
        "windll",
        SimpleNamespace(kernel32=SimpleNamespace(GetUserDefaultUILanguage=lambda: 0x0412)),
        raising=False,
    )
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: ("ko_KR", "UTF-8"))
    assert i18n.system_language() == "en"
