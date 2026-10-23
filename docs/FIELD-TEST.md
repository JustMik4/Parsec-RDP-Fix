# Experimental evidence — October 22, 2026

## Baseline: service-launched Parsec disconnects RDP

Windows TerminalServices LocalSessionManager emitted event ID 59 `RpcLogoff`, naming `C:\Program Files\Parsec\parsecd.exe` with `SERVICE_LAUNCHED_V13` during a remote connection. Event ID 23 then confirmed the independent RDP user's session was logged off. The normal host could still stream video, but the separate RDP workspace was terminated.

## A/B: same installed Parsec in user mode

The Parsec service was stopped and lingering service-launched processes were closed. The **original installed** Parsec 150.105c was started directly by the console user's ordinary token, retaining its profile in `%APPDATA%\Parsec`.

Its log showed `Service: -1, Loader: 18` and no `SERVICE_LAUNCHED_V13` process argument.

At **23:16:09 local time**, a remote client connected to that original Parsec host, and AMD video encoding started. The independent Windows RDP session (ID 4) stayed Active. The Parsec service was restored to Running in the same boot **after the ordinary user host was already running**; the installed Parsec continued streaming without a new `RpcLogoff`. A separate portable fallback was closed, and the original host continued streaming through 23:21.

**What this proves:** The ordinary-user launch order worked for a real remote connection on the tested machine. **What it does not prove:** A persistent service start-type change after reboot, preservation of remote login-screen access, repeated reconnect reliability, or universal compatibility.

The new Parsec RDP Fix utility automates this sequence. It has not yet been applied end-to-end to the live computer, so this evidence is a manual experiment, not a validation of the release executable.

The full local diagnostic traces are not included in the public repo because they may include local usernames, account identifiers or session details.
