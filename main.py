"""Portable Windows entry point. Administrator approval is required to run."""

import ctypes
import sys
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from parsec_rdp_fix import engine
from parsec_rdp_fix.ui import FixWindow


def main():
    if not engine.is_admin():
        if getattr(sys, "frozen", False):
            messagebox.showerror(
                "Administrator access required",
                "Restart Parsec RDP Fix as administrator to apply or restore the fix.",
            )
            return

        script = Path(__file__).resolve()
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}"', str(script.parent), 1
        )
        if result <= 32:
            messagebox.showerror("Administrator access required", "Administrator approval was denied.")
        return

    FixWindow().mainloop()


if __name__ == "__main__":
    main()
