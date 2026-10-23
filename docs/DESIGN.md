# Implementation and rollback

## Privilege separation

**The utility does not launch a second elevated worker.** The portable executable declares `requireAdministrator` in its Windows manifest. The GUI starts elevated after UAC approval.

Clicking Apply or Restore starts a short-lived **worker thread in the same process**. Progress is delivered to the GUI through a Python queue. No temporary status files, external elevated Python worker, or process-PID polling are needed.

Service configuration, process termination and registry-backup operations require administrator rights. The **installed Parsec host must not inherit those rights**. To start it, the utility:

1. Locates `explorer.exe` processes in the GUI's own Windows session.
2. Opens a shell process's Windows access token.
3. Verifies that the shell token belongs to the same account and has standard/medium integrity.
4. Duplicates that token as a primary token.
5. Calls `CreateProcessWithTokenW` using `LOGON_WITH_PROFILE` to start the original installed `parsecd.exe`.
6. Verifies that the installed host is running without `SERVICE_LAUNCHED_V13`.

It does **not** borrow a token from another Windows user, start Parsec as SYSTEM, disable Windows signature verification, or modify a Parsec binary.

## Applying

- Validate the per-user installation and service executable.
- Back up the existing service start type (Automatic/Manual) and user's Parsec Run entry in `HKCU\Software\ParsecRDPFix\Backup`.
- Stop the Parsec service and shut down its installed host processes, limiting process cleanup to the active desktop session and associated service helper.
- Temporarily switch the service to Manual.
- Start the installed Parsec from the ordinary user's medium-integrity shell and wait for a valid process.
- Restart the Parsec service; configure future startup as Disabled.
- Check that the user-mode Parsec host remains active. The GUI can now exit.

If the apply stage fails, the worker attempts to return the service to its saved startup type, start the service and roll back the incomplete user Run backup. Any incomplete recovery is reported explicitly.

## Restoring

- Read the saved backup and require administrator rights.
- Stop the original host and service.
- Restore the previously saved service startup mode and start the service.
- Restore the original user Run value.
- Open the existing Parsec executable as the ordinary shell user.

A missing backup is not an invitation to invent the previous configuration; the Restore button remains disabled.

## Known limitations

The current version detects the mode of the running host using its executable path and absence of the service-launch argument. It does not independently test a remote video stream or guarantee that the Parsec service will not take over the host on later reconnects.

The user must already be logged in to Windows to obtain their normal Explorer shell token. UAC elevation under a different Windows account is not supported. A restart or Parsec update might change service startup or host behavior.

The workaround's underlying manual A/B experiment succeeded for one Windows 11 setup, but the latest automated executable has **not yet undergone a full live apply / reconnect / reboot field test**.

## Tests

Automated tests mock privileged changes, validate service ordering and rollback, ensure a process from a different RDP session is not killed by cleanup, exercise localized GUI actions and check native token structures.

A separate harmless Windows test launched a console command with medium integrity from an elevated process using the same native routine. It did not stop Parsec or TermService.
