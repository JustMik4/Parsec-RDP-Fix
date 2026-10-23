"""Ensure the standalone Windows release includes essential Tcl/Tk resources."""

import sys
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

exe = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/ParsecRDPFix.exe")
if not exe.is_file():
    raise SystemExit(f"Release executable not found: {exe}")

members = {
    name.replace("\\", "/").casefold() for name in CArchiveReader(str(exe)).toc
}
required = ("_tcl_data/init.tcl", "_tk_data/tk.tcl", "_tk_data/spinbox.tcl")
missing = [name for name in required if name not in members]
if missing:
    raise SystemExit(f"Release is missing Tcl/Tk files: {', '.join(missing)}")

print("Packaged Tcl/Tk runtime files verified.")
