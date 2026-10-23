"""Regression tests for swapping independent theme pages."""

from parsec_rdp_fix.ui import PALETTES, FixWindow


def test_theme_pages_have_independent_native_canvases():
    window = FixWindow()
    try:
        window.update()
        dark = window._views["dark"]
        light = window._views["light"]
        assert dark["page"] is not light["page"]
        assert dark["body"] is not light["body"]
        assert dark["footer"] is not light["footer"]
        assert dark["theme_button"] is not light["theme_button"]
        assert dark["body"]._parent_canvas.cget("bg") == PALETTES["dark"]["BACKGROUND"]
        assert light["body"]._parent_canvas.cget("bg") == PALETTES["light"]["BACKGROUND"]
        assert dark["page"].cget("fg_color") == PALETTES["dark"]["BACKGROUND"]
        assert light["page"].cget("fg_color") == PALETTES["light"]["BACKGROUND"]
    finally:
        window.destroy()


def test_background_status_update_survives_a_theme_switch():
    window = FixWindow()
    try:
        window.update()
        window._show_message("progress_service")
        window.operation = "apply"
        window._update_buttons()
        window._toggle_theme()

        assert window.message.cget("text") == window.t("progress_service")
        assert window.apply_button.cget("state") == "disabled"
        assert window.restore_button.cget("state") == "disabled"
        assert window._views["dark"]["page"].winfo_exists()
        assert window._views["light"]["page"].winfo_exists()
    finally:
        window.destroy()


def test_translator_updates_hidden_page_when_shown():
    window = FixWindow()
    try:
        window.update()
        window._change_language("Русский")
        assert window.translator.language == "ru"
        window._toggle_theme()
        assert window.labels["risk_2"].cget("text") == window.t("risk_2")
        assert window.language.get() == "Русский"
        window._toggle_theme()
        assert window.labels["risk_2"].cget("text") == window.t("risk_2")
    finally:
        window.destroy()
