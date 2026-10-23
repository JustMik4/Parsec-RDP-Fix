# Warnings and recovery

**This utility changes a remote-control service. Always keep a separate recovery method.**

- Applying and restoring will close Parsec and disconnect Parsec clients.
- Access to the Windows login screen, secure UAC, elevated programs and privileged input/capture may be unavailable.
- Some virtual controllers or capture features can stop working.
- After reboot, Parsec may start only after the Windows desktop user signs in.
- Subsequent Parsec updates may change the service startup policy or launch order.
- The observed successful workaround is not a universal guarantee for Windows and Parsec versions.

The program requests Windows administrator approval when opening. It does **not** require you to launch an unelevated helper. The installed Parsec application is the only process started with standard user permissions during the patch.

Restore defaults is offered only when the utility previously stored a valid backup. The backup is kept in the user's Windows registry, not beside the portable executable, and remains when that executable is deleted.

If you lose remote access, sign into Windows locally or using an independent method. Windows Services (`services.msc`) can restore the Parsec service's Automatic startup type if necessary.

**Release gate:** live application, successful remote reconnect and persistence across reboot remain unverified for the new automated patch implementation. Do not advertise those as completed.
