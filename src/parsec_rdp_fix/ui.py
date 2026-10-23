"""Compact Windows desktop interface for Parsec RDP Fix."""

from __future__ import annotations

import queue
import threading
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

from . import engine, worker
from .i18n import LANGUAGES, Translator
from .icons import make_icon

GITHUB = "https://github.com/JustMik4/Parsec-RDP-Fix"

PALETTES = {
    "dark": {
        "BACKGROUND": "#171B1D",
        "SURFACE": "#22282A",
        "BORDER": "#394144",
        "TEXT": "#EEF1EF",
        "SUBTLE": "#A6AFB1",
        "GREEN": "#88BBA2",
        "GREEN_DARK": "#497560",
        "ACTION": "#426D58",
        "ACTION_HOVER": "#527E67",
        "ACTION_TEXT": "#F7F8F7",
        "WARNING": "#F0B578",
        "WARNING_BORDER": "#91623C",
        "WARNING_BG": "#34291F",
        "WARNING_TEXT": "#F1DBC5",
        "WARNING_RULE": "#775235",
        "HEADER_HOVER": "#313A3C",
        "MENU_BUTTON": "#313A3C",
        "MENU_HOVER": "#435052",
        "MENU_SELECTED": "#40504A",
        "NUMBER": "#97B5A4",
        "RESTORE_HOVER": "#303739",
        "RESTORE_BORDER": "#566064",
        "CHECK_BORDER": "#879093",
        "SCROLL": "#596366",
        "SCROLL_HOVER": "#707C7E",
    },
    "light": {
        "BACKGROUND": "#EBEEEC",
        "SURFACE": "#F9FAF9",
        "BORDER": "#CFD3D0",
        "TEXT": "#1D2528",
        "SUBTLE": "#586167",
        "GREEN": "#376C58",
        "GREEN_DARK": "#29523F",
        "ACTION": "#376C58",
        "ACTION_HOVER": "#29523F",
        "ACTION_TEXT": "#FFFFFF",
        "WARNING": "#A45721",
        "WARNING_BORDER": "#DCA36E",
        "WARNING_BG": "#FFF0DF",
        "WARNING_TEXT": "#513B29",
        "WARNING_RULE": "#DBAD80",
        "HEADER_HOVER": "#DEE5E1",
        "MENU_BUTTON": "#E3E8E4",
        "MENU_HOVER": "#D4DED7",
        "MENU_SELECTED": "#E7EDE9",
        "NUMBER": "#728D80",
        "RESTORE_HOVER": "#E6EBE7",
        "RESTORE_BORDER": "#B9C1BC",
        "CHECK_BORDER": "#78827D",
        "SCROLL": "#BCC7BF",
        "SCROLL_HOVER": "#ABB9AE",
    },
}

FONT = "Segoe UI"
FONT_ZH = "Microsoft YaHei UI"
FONT_JA = "Yu Gothic UI"
LANGUAGE_NAMES = {value: key for key, value in LANGUAGES.items()}


def text_font(size: int = 13, weight: str = "normal", family: str = FONT) -> ctk.CTkFont:
    return ctk.CTkFont(family=family, size=size, weight=weight)


class FixWindow(ctk.CTk):
    VIEW_WIDGETS = (
        "page",
        "header",
        "body",
        "footer",
        "labels",
        "repository",
        "language",
        "theme_icon",
        "theme_button",
        "warning_icon",
        "warning_icon_label",
        "service_state",
        "host_state",
        "consent",
        "message",
        "restore_button",
        "apply_button",
    )

    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=PALETTES["dark"]["BACKGROUND"])
        self.title("Parsec RDP Fix")
        self.geometry("1000x730")
        self.minsize(860, 680)
        self.translator = Translator()
        self.font_family = FONT
        self.acknowledged = ctk.BooleanVar(value=False)
        self.operation: str | None = None
        self.events = queue.SimpleQueue()
        self.system_state = None
        self.last_message_key = "ready"
        self.last_error = ""
        self._theme_assets = self._preload_theme_assets()
        self._views = {}

        # Fully construct both independent themes before showing the window.
        for name in ("dark", "light"):
            self.colors = PALETTES[name]
            self.dark_mode = name == "dark"
            self.labels = {}
            self._build_interface()
            self._views[name] = {key: getattr(self, key) for key in self.VIEW_WIDGETS}

        self._select_view("dark")
        self.page.tkraise()
        self.after(250, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _select_view(self, name: str):
        self.colors = PALETTES[name]
        self.dark_mode = name == "dark"
        for attribute, widget in self._views[name].items():
            setattr(self, attribute, widget)

    def _build_interface(self):
        self.page = ctk.CTkFrame(self, fg_color=self.colors["BACKGROUND"], corner_radius=0)
        self.page.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.page.grid_columnconfigure(0, weight=1)
        self.page.grid_rowconfigure(1, weight=1)
        self._header()

        self.body = ctk.CTkScrollableFrame(
            self.page,
            fg_color=self.colors["BACKGROUND"],
            bg_color=self.colors["BACKGROUND"],
            scrollbar_button_color=self.colors["SCROLL"],
            scrollbar_button_hover_color=self.colors["SCROLL_HOVER"],
            corner_radius=0,
        )
        self.body.grid(row=1, column=0, sticky="nsew", padx=32, pady=(6, 14))
        self.body.grid_columnconfigure(0, weight=1)
        for row in range(4):
            self.body.grid_rowconfigure(row, weight=0)

        self._status_section()
        self._steps_section()
        self._warning_section()
        self._acknowledgement()
        self._footer()
        self._translate()
        self.refresh()

    def t(self, key: str) -> str:
        return self.translator(key)

    def _label(self, parent, key: str, size=13, weight="normal", color=None, **kwargs):
        item = ctk.CTkLabel(
            parent,
            text=self.t(key),
            anchor="w",
            font=text_font(size, weight, self.font_family),
            text_color=color or self.colors["TEXT"],
            height=20,
            **kwargs,
        )
        self.labels[key] = item
        return item

    def _header(self):
        header = ctk.CTkFrame(self.page, fg_color="transparent")
        self.header = header
        header.grid(row=0, column=0, sticky="ew", padx=34, pady=(23, 11))
        header.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            left,
            text="Parsec RDP Fix",
            text_color=self.colors["TEXT"],
            font=text_font(30, "bold"),
            anchor="w",
        ).pack(anchor="w")
        self._label(left, "subtitle", 14, color=self.colors["SUBTLE"]).pack(anchor="w", pady=(0, 1))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        self.repository = ctk.CTkButton(
            right,
            text="Open source ↗",
            command=lambda: webbrowser.open(GITHUB),
            fg_color="transparent",
            hover_color=self.colors["HEADER_HOVER"],
            text_color=self.colors["GREEN"],
            font=ctk.CTkFont(family=FONT, size=13, weight="bold", underline=True),
            height=31,
            width=124,
            corner_radius=5,
        )
        self.repository.pack(side="left", padx=(0, 14))
        self.language = ctk.CTkOptionMenu(
            right,
            values=list(LANGUAGES.values()),
            width=137,
            height=31,
            fg_color=self.colors["SURFACE"],
            button_color=self.colors["MENU_BUTTON"],
            button_hover_color=self.colors["MENU_HOVER"],
            dropdown_fg_color=self.colors["SURFACE"],
            dropdown_hover_color=self.colors["MENU_SELECTED"],
            text_color=self.colors["TEXT"],
            font=text_font(12),
            dropdown_text_color=self.colors["TEXT"],
            dropdown_font=text_font(12),
            command=self._change_language,
        )
        self.language.set(LANGUAGES[self.translator.language])
        self.language.pack(side="left")
        self.theme_icon = self._theme_assets["dark" if self.dark_mode else "light"]["theme"]
        self.theme_button = ctk.CTkButton(
            right,
            text="",
            image=self.theme_icon,
            width=36,
            height=32,
            fg_color="transparent",
            hover_color=self.colors["HEADER_HOVER"],
            corner_radius=6,
            command=self._toggle_theme,
        )
        self.theme_button.pack(side="left", padx=(11, 0))

    def _preload_theme_assets(self):
        assets = {}
        for theme, colors in PALETTES.items():
            assets[theme] = {
                "theme": ctk.CTkImage(
                    light_image=make_icon("sun" if theme == "dark" else "moon", colors["TEXT"]),
                    dark_image=make_icon("sun" if theme == "dark" else "moon", colors["TEXT"]),
                    size=(20, 20),
                ),
                "warning": ctk.CTkImage(
                    light_image=make_icon("warning", colors["WARNING"]),
                    dark_image=make_icon("warning", colors["WARNING"]),
                    size=(22, 22),
                ),
            }
        return assets

    def _toggle_theme(self):
        """Switch to a fully rendered page with no intermediate color changes."""
        target = "light" if self.dark_mode else "dark"
        position = self.body._parent_canvas.yview()
        self._select_view(target)
        self.body._parent_canvas.yview_moveto(position[0] if position else 0.0)
        self.language.set(LANGUAGES[self.translator.language])
        self._translate()
        self._update_buttons()
        self.page.tkraise()

    def _panel(self, row: int, border=None, bg=None, vertical=10):
        section = ctk.CTkFrame(
            self.body,
            fg_color=bg or self.colors["SURFACE"],
            border_width=1,
            border_color=border or self.colors["BORDER"],
            corner_radius=9,
        )
        section.grid(row=row, column=0, sticky="ew", pady=(0, vertical))
        return section

    def _section_title(self, parent, key: str, color=None):
        self._label(parent, key, 15, "bold", color or self.colors["TEXT"]).pack(
            anchor="w", padx=20, pady=(9, 3)
        )

    def _divider(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color=self.colors["BORDER"], corner_radius=0).pack(
            fill="x", padx=20, pady=(0, 6)
        )

    def _status_section(self):
        panel = self._panel(0)
        self._section_title(panel, "status_title")
        self._divider(panel)

        columns = ctk.CTkFrame(panel, fg_color="transparent")
        columns.pack(fill="x", padx=20, pady=(0, 8))
        columns.grid_columnconfigure((0, 1), weight=1)

        service = ctk.CTkFrame(columns, fg_color="transparent")
        service.grid(row=0, column=0, sticky="w", padx=(10, 8))
        self._label(service, "service", 13, "bold").pack(anchor="w")
        self.service_state = ctk.CTkLabel(
            service, text="—", text_color=self.colors["SUBTLE"], font=text_font(13), anchor="w"
        )
        self.service_state.pack(anchor="w", pady=(2, 0))

        host = ctk.CTkFrame(columns, fg_color="transparent")
        host.grid(row=0, column=1, sticky="w", padx=(10, 8))
        self._label(host, "host", 13, "bold").pack(anchor="w")
        self.host_state = ctk.CTkLabel(
            host, text="—", text_color=self.colors["SUBTLE"], font=text_font(13), anchor="w"
        )
        self.host_state.pack(anchor="w", pady=(2, 0))

    def _steps_section(self):
        panel = self._panel(1)
        self._section_title(panel, "changes")
        self._divider(panel)
        table = ctk.CTkFrame(panel, fg_color="transparent")
        table.pack(fill="x", padx=24, pady=(0, 5))
        table.grid_columnconfigure((0, 1), weight=1, uniform="steps")

        for index in range(4):
            row, col = divmod(index, 2)
            wrapper = ctk.CTkFrame(table, fg_color="transparent")
            wrapper.grid(row=row, column=col, sticky="ew", padx=(0, 10), pady=5)
            number = ctk.CTkLabel(
                wrapper,
                text=f"{index + 1:02}",
                font=text_font(23),
                text_color=self.colors["NUMBER"],
                width=46,
                anchor="w",
            )
            number.pack(side="left", anchor="n", padx=(0, 12))
            descriptions = ctk.CTkFrame(wrapper, fg_color="transparent")
            descriptions.pack(side="left", fill="x", expand=True)
            self._label(descriptions, f"step_{index + 1}", 13, "bold").pack(anchor="w")
            self._label(
                descriptions,
                f"step_{index + 1}_desc",
                12,
                color=self.colors["SUBTLE"],
                wraplength=330,
                justify="left",
            ).pack(anchor="w", pady=(1, 0))
        self._label(panel, "app_note", 12, color=self.colors["GREEN"]).pack(anchor="w", padx=24, pady=(0, 8))

    def _warning_section(self):
        panel = self._panel(2, self.colors["WARNING_BORDER"], self.colors["WARNING_BG"], vertical=7)
        heading = ctk.CTkFrame(panel, fg_color="transparent")
        heading.pack(fill="x", padx=19, pady=(10, 6))
        self.warning_icon = self._theme_assets["dark" if self.dark_mode else "light"]["warning"]
        self.warning_icon_label = ctk.CTkLabel(heading, text="", image=self.warning_icon, width=25)
        self.warning_icon_label.pack(side="left", padx=(0, 9))
        self._label(heading, "read_before", 15, "bold", self.colors["WARNING"]).pack(side="left")
        for index in range(1, 6):
            row = ctk.CTkFrame(panel, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=0)
            ctk.CTkLabel(row, text="•", font=text_font(14), text_color=self.colors["WARNING"], width=17).pack(
                side="left", anchor="n"
            )
            self._label(
                row,
                f"risk_{index}",
                12,
                color=self.colors["WARNING_TEXT"],
                wraplength=875,
                justify="left",
            ).pack(side="left", anchor="w", fill="x", expand=True)
        ctk.CTkFrame(panel, height=1, fg_color=self.colors["WARNING_RULE"]).pack(
            fill="x", padx=20, pady=(6, 8)
        )

    def _acknowledgement(self):
        self.consent = ctk.CTkCheckBox(
            self.body,
            text=self.t("ack"),
            variable=self.acknowledged,
            onvalue=True,
            offvalue=False,
            command=self._update_buttons,
            checkmark_color=self.colors["SURFACE"],
            fg_color=self.colors["ACTION"],
            hover_color=self.colors["ACTION_HOVER"],
            border_color=self.colors["CHECK_BORDER"],
            text_color=self.colors["TEXT"],
            font=text_font(12),
            checkbox_height=20,
            checkbox_width=20,
            height=28,
            corner_radius=4,
        )
        self.consent.grid(row=3, column=0, sticky="w", padx=4, pady=1)

    def _footer(self):
        self.footer = ctk.CTkFrame(self.page, fg_color=self.colors["SURFACE"], corner_radius=0)
        self.footer.grid(row=2, column=0, sticky="ew")
        self.footer.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(self.footer, height=1, fg_color=self.colors["BORDER"], corner_radius=0).grid(
            row=0, column=0, columnspan=3, sticky="ew"
        )
        self.message = ctk.CTkLabel(
            self.footer,
            text="",
            font=text_font(12),
            text_color=self.colors["SUBTLE"],
            anchor="w",
            wraplength=500,
        )
        self.message.grid(row=1, column=0, sticky="ew", padx=(33, 10), pady=15)

        self.restore_button = ctk.CTkButton(
            self.footer,
            text=self.t("restore"),
            fg_color=self.colors["SURFACE"],
            hover_color=self.colors["RESTORE_HOVER"],
            text_color=self.colors["TEXT"],
            border_width=1,
            border_color=self.colors["RESTORE_BORDER"],
            font=text_font(13, "bold"),
            width=180,
            height=39,
            corner_radius=7,
            command=self._restore,
        )
        self.restore_button.grid(row=1, column=1, padx=(0, 9), pady=12)
        self.apply_button = ctk.CTkButton(
            self.footer,
            text=self.t("apply"),
            fg_color=self.colors["ACTION"],
            hover_color=self.colors["ACTION_HOVER"],
            text_color=self.colors["ACTION_TEXT"],
            font=text_font(13, "bold"),
            width=195,
            height=39,
            corner_radius=7,
            command=self._apply,
        )
        self.apply_button.grid(row=1, column=2, padx=(0, 31), pady=12)

    def _change_language(self, name: str):
        self.translator.set_language(LANGUAGE_NAMES[name])
        self._translate()

    def _translate(self):
        self.font_family = (
            FONT_ZH
            if self.translator.language == "zh"
            else FONT_JA
            if self.translator.language == "ja"
            else FONT
        )
        for key, widget in self.labels.items():
            current = widget.cget("font")
            widget.configure(
                text=self.t(key),
                font=text_font(current.cget("size"), current.cget("weight"), self.font_family),
            )
        self.consent.configure(text=self.t("ack"), font=text_font(12, family=self.font_family))
        self.apply_button.configure(text=self.t("apply"))
        self.restore_button.configure(text=self.t("restore"))
        self._draw_state()
        self._show_message(self.last_message_key, self.last_error)

    def refresh(self):
        try:
            self.system_state = engine.snapshot()
        except (engine.PatchError, OSError, ValueError):
            self.system_state = None
        self._draw_state()
        self._update_buttons()

    def _draw_state(self):
        state = self.system_state
        if state is None:
            self.service_state.configure(text=self.t("unknown"), text_color=self.colors["WARNING"])
            self.host_state.configure(text=self.t("unknown"), text_color=self.colors["SUBTLE"])
            return

        mode = {2: "automatic", 3: "manual", 4: "disabled"}.get(state.service_start, "unknown")
        current = "running" if state.service_running else "stopped"
        self.service_state.configure(
            text=f"●   {self.t(current)}  ·  {self.t(mode)}",
            text_color=self.colors["GREEN"] if state.service_running else self.colors["SUBTLE"],
        )
        self.host_state.configure(
            text=f"●   {self.t('patched' if state.patched else 'original')}",
            text_color=self.colors["GREEN"] if state.patched else self.colors["SUBTLE"],
        )

    def _show_message(self, key: str, detail: str = ""):
        self.last_message_key, self.last_error = key, detail
        message = self.t(key)
        if detail:
            message += "  " + detail
        self.message.configure(
            text=message,
            text_color=self.colors["WARNING"] if key.startswith("progress_error") else self.colors["SUBTLE"],
        )

    def _update_buttons(self):
        busy = self.operation is not None
        self.apply_button.configure(
            state="normal"
            if self.acknowledged.get()
            and not busy
            and self.system_state is not None
            and self.system_state.backup is None
            and self.system_state.service_start != engine.START_DISABLED
            else "disabled"
        )
        self.restore_button.configure(
            state="normal"
            if not busy and self.system_state is not None and self.system_state.backup
            else "disabled"
        )

    def _apply(self):
        if not engine.is_admin():
            messagebox.showerror(self.t("elevation_title"), self.t("elevation_detail"), parent=self)
            return
        if not messagebox.askyesno(self.t("consent_title"), self.t("consent_apply"), parent=self):
            return
        self._begin("apply")

    def _restore(self):
        if not engine.is_admin():
            messagebox.showerror(self.t("elevation_title"), self.t("elevation_detail"), parent=self)
            return
        if not messagebox.askyesno(self.t("consent_title"), self.t("consent_restore"), parent=self):
            return
        self._begin("restore")

    def _begin(self, action: str):
        if self.operation is not None:
            return
        self.operation = action
        self._show_message("progress_started")
        self._update_buttons()
        threading.Thread(target=self._execute, args=(action,), daemon=True).start()

    def _execute(self, action: str):
        try:
            task = worker.apply if action == "apply" else worker.restore
            task(lambda phase: self.events.put(("progress", phase)))
        except Exception as error:
            self.events.put(("error", str(error)))
        else:
            self.events.put(("done", ""))

    def _poll(self):
        while True:
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "progress":
                self._show_message("progress_" + value)
            else:
                self._finish(event, value)

        self.after(250, self._poll)

    def _finish(self, outcome: str, detail: str):
        self.operation = None
        if outcome == "error":
            self._show_message("progress_error")
            messagebox.showerror(self.t("error_title"), detail, parent=self)
        else:
            self._show_message("progress_done")
        self.refresh()

    def _close(self):
        if self.operation is not None:
            messagebox.showwarning(self.t("consent_title"), self.t("progress_stopping"), parent=self)
            return
        self.destroy()
