import hashlib
from pathlib import Path

path = Path("dist/ParsecRDPFix.exe")
digest = hashlib.sha256(path.read_bytes()).hexdigest()
Path("dist/SHA256SUMS.txt").write_text(
    f"{digest}  {path.name}\n", encoding="ascii"
)
print(f"SHA256 {digest}")
