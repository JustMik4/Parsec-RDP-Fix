# Parsec RDP Fix v0.1.0

**First public release** — based on the locally validated dual-page interface and original installed-host workaround.

## Features

- Portable `ParsecRDPFix.exe` for Windows 10/11 x64 (administrator approval required).
- Apply a one-time installed-host configuration; no resident helper or installation.
- Restore the original startup settings from a previous backup.
- Launch the installed Parsec host as the desktop user, not as a privileged service-launched host.
- Six UI languages and reliable instant dark/light switching.
- Automated source tests, MIT license, and SHA-256 checksum.

## Safety and known limitations

**Applying or restoring disconnects Parsec.** Have physical or separate remote access. Some Parsec features for the login screen, UAC, elevated applications, capture or virtual devices may be unavailable. Signing in locally after reboot may be required.

The underlying host-launch technique was demonstrated on one Windows 11 configuration, but the automated release's complete apply/reconnect sequence and reboot persistence have not been broadly verified. Compatibility depends on the Windows and Parsec version.

This unofficial community project is not affiliated with Parsec. It does not patch or redistribute proprietary Parsec binaries. The executable is **not digitally signed**.

Compare the release executable's SHA-256 to the accompanying `SHA256SUMS.txt`.
