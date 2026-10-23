# Parsec RDP Fix

A portable, open-source Windows utility for a specific Parsec host and RDP session conflict.

On an observed Windows 11 configuration, connecting through the service-launched Parsec host caused Windows to log off a separate RDP user. Running the **original installed Parsec host as the desktop user**, instead of as a privileged service-launched process, allowed both sessions to remain connected during a field experiment.

This project automates that configuration without modifying or redistributing Parsec binaries, DLLs, credentials, Windows RDP files, or drivers. **Unofficial community project — not affiliated with Parsec.**

> [!WARNING]
> Applying or restoring the fix interrupts existing Parsec connections. Have physical access or another independent remote connection before proceeding. Post-reboot compatibility and every Parsec feature have not been verified across Windows and Parsec versions.

## Download

**Windows 10/11 x64 — [Download from GitHub Releases](https://github.com/JustMik4/Parsec-RDP-Fix/releases)**

Download `ParsecRDPFix.exe` and open it. Windows requests administrator permission. The utility is portable; it does not install itself or need to remain open after applying the fix.

The executable is currently unsigned, so Windows may display an unknown-publisher warning. Verify the SHA-256 against the accompanying `SHA256SUMS.txt`.

## How it works

1. Detect the supported installed Parsec executable, its service, and the user's configuration.
2. Save the original service startup mode and Windows user Run entry to `HKCU\Software\ParsecRDPFix`.
3. Stop the Parsec service and affected host processes, disconnecting existing Parsec clients.
4. Launch the **same installed Parsec executable** using the account's non-elevated Explorer token.
5. Restart the service after the desktop-user host is running, then disable automatic service startup for subsequent boots.
6. Verify the user-mode host is still running.

**Restore defaults** is available only when a valid backup was saved. Restoration interrupts Parsec, returns the recorded Windows settings, and may bring back the original RDP conflict.

The UI has English, Portuguese, Spanish, Russian, Simplified Chinese, and Japanese translations. It follows the Windows display language when supported and defaults to English otherwise. Dark mode is the default; an instant light/dark toggle is provided.

## Important limitations

- Parsec may only become available after signing in to the Windows desktop following reboot.
- Parsec features for the sign-in screen, secure UAC, elevated applications, virtual controllers, or screen capture may be limited.
- Parsec updates may change the host or service startup behavior.
- An interactive, same-account Explorer session is required; elevation through another admin account is not supported.
- The tool does **not** enable concurrent RDP sessions. Configuring RDP is outside this project's scope.
- The field experiment succeeded on one machine; the automated public build's **post-reboot reliability is not universally established**.

Review [limitations and recovery](docs/LIMITATIONS.md), [implementation details](docs/DESIGN.md), and [the field experiment](docs/FIELD-TEST.md).

## Build from source

Requires Windows, Python 3.12+, and PowerShell.

```powershell
git clone https://github.com/JustMik4/Parsec-RDP-Fix.git
cd Parsec-RDP-Fix
.\scripts\build.ps1
```

The build script creates `.venv`, runs tests and Ruff, and generates `dist/ParsecRDPFix.exe` with `dist/SHA256SUMS.txt`. GitHub Actions performs the same build and prepares a draft release when a version tag is pushed.

See [UI and localization](docs/UI-DESIGN.md), [security policy](SECURITY.md), and [changelog](CHANGELOG.md).

## License

MIT covers this repository's original code. Parsec is proprietary and is neither distributed nor endorsed by this utility.
