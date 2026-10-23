# Security policy

Parsec RDP Fix is an open-source configuration utility, not an official Parsec component.

It needs administrator permission only for changing the Parsec Windows service. The utility runs as administrator; only the installed Parsec host is launched with the desktop user's ordinary token.

It does not patch signed Parsec binaries, bypass signature verification, read Parsec login tokens, or disable RDP security controls.

The UI explicitly warns that applying the change will interrupt Parsec connections and may remove pre-login, UAC, elevated-application and virtual device support.

The application doesn't send telemetry or communicate with the network. A small configuration backup is stored under the current user's registry hive. Keep independent access to a PC when changing its remote access service.

Please open a private GitHub security advisory (after the repository is published) for security issues. Do not paste Parsec account secrets, Peer IDs or `user.bin` into public issues.
