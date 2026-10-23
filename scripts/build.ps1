$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    python -m venv .venv
}
$python = '.venv\Scripts\python.exe'
& $python -m pip install --disable-pip-version-check -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $python -m ruff check src main.py tests
if ($LASTEXITCODE -ne 0) { throw 'Lint failed' }
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin --name ParsecRDPFix --paths src --collect-all customtkinter --add-data "locales;locales" main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
& $python scripts\checksum.py
if ($LASTEXITCODE -ne 0) { throw 'Checksum generation failed' }
Write-Output 'Release binary: dist\ParsecRDPFix.exe'
