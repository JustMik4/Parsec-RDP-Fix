"""Two prebuilt theme pages and translated warning text."""

import json

from parsec_rdp_fix.i18n import LANGUAGES, catalog_dir
from parsec_rdp_fix.icons import make_icon
from parsec_rdp_fix.ui import PALETTES, FixWindow


def test_both_themes_have_matching_color_roles():
    assert set(PALETTES) == {"dark", "light"}
    assert set(PALETTES["dark"]) == set(PALETTES["light"])
    assert PALETTES["dark"]["BACKGROUND"] != PALETTES["light"]["BACKGROUND"]
    assert PALETTES["dark"]["WARNING_BG"] != PALETTES["dark"]["SURFACE"]
    assert PALETTES["light"]["WARNING_BG"] != PALETTES["light"]["SURFACE"]


def test_theme_icons_are_transparent_and_readable():
    for kind in ("sun", "moon", "warning"):
        icon = make_icon(kind, "#F0B578")
        assert icon.size == (80, 80)
        assert icon.getchannel("A").getextrema() == (0, 255)


def test_switches_prebuilt_pages_without_changing_appearance():
    import customtkinter as ctk

    window = FixWindow()
    try:
        window.update()
        pages = {key: view["page"] for key, view in window._views.items()}
        original_colors = {key: view["body"]._parent_canvas.cget("bg") for key, view in window._views.items()}
        assert window.dark_mode
        assert ctk.get_appearance_mode() == "Dark"
        assert original_colors == {
            "dark": PALETTES["dark"]["BACKGROUND"],
            "light": PALETTES["light"]["BACKGROUND"],
        }

        window.acknowledged.set(True)
        window.translator.set_language("es")
        window._translate()
        window.operation = "apply"
        window._update_buttons()

        for theme in ("light", "dark", "light", "dark", "light"):
            window._toggle_theme()
            window.update_idletasks()
            assert window.dark_mode == (theme == "dark")
            assert window.page is pages[theme]
            assert window.body._parent_canvas.cget("bg") == PALETTES[theme]["BACKGROUND"]
            assert window.labels["read_before"].cget("text_color") == PALETTES[theme]["WARNING"]
            assert window.translator.language == "es"
            assert window.labels["read_before"].cget("text") == window.t("read_before")
            assert window.acknowledged.get()
            assert window.operation == "apply"
            assert window.apply_button.cget("state") == "disabled"
            assert ctk.get_appearance_mode() == "Dark"

        assert all(window._views[key]["page"] is page for key, page in pages.items())
    finally:
        window.destroy()


def test_warning_names_parsec_in_every_language():
    for language in LANGUAGES:
        catalog = json.loads((catalog_dir() / f"{language}.json").read_text(encoding="utf-8"))
        assert "Parsec" in catalog["risk_2"]
        assert catalog["risk_2"].strip()
