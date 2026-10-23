# Interface and localization

The app follows a restrained Windows utility layout: a concise title, service and host state, four steps, a focused warning and a fixed action bar. The dark charcoal theme is the default; the light variant has a soft-gray background.

## Double-buffered theme pages

The theme switch is an **instant swap between two fully constructed pages**. Each page owns its header, scrollable body, footer and native scroll canvas, with fixed, explicit colors from its own palette.

Both pages are created once during startup, and the dark page is raised before first display. On a theme toggle, the program selects the alternate page, synchronizes language, scroll position, operation state and button availability, then raises that page. It **does not** call `set_appearance_mode` again, recolor existing widgets, rebuild widgets or take screen captures.

Earlier versions used global appearance updates and screenshots, causing old canvas colors, mixed light/dark elements and noticeable flicker. The native CTkScrollableFrame canvas inherits its background and can lag global theme updates. Using two pages avoids this class of issue rather than masking it with animation. Switching is immediate rather than a potentially unstable animated fade.

The two page trees use modest additional memory for reliability. The patch engine, service configuration, user-token handling and account data are unaffected by theme changes.

References:
- https://customtkinter.tomschimansky.com/documentation/widgets/scrollableframe/
- https://github.com/TomSchimansky/CustomTkinter/blob/master/customtkinter/windows/widgets/ctk_scrollable_frame.py
- https://learn.microsoft.com/en-us/windows/apps/design/guidelines-overview

## Languages

The Open source action links to https://github.com/JustMik4/Parsec-RDP-Fix.

The interface supports Portuguese, English, Spanish, Russian, Simplified Chinese and Japanese through UTF-8 catalogs in `locales/`. The Windows user interface language determines the initial language, falling back to English. The selection can be changed at runtime and is synchronized when switching themes.

All executable source, comments, identifiers, tests and documentation use English. The warning triangle and sun/moon icons are vector-drawn locally using Pillow; no external images are downloaded.

## Application operations

The portable Windows executable requests administrator permission on launch. Apply and Restore execute in a worker thread and report status through a thread-safe queue. The installed Parsec host is launched with a same-user, medium-integrity Windows shell token, not as an elevated child.

The dual-page UI is independent of this privilege-separation logic.
