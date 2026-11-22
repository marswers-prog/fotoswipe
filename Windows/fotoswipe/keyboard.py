"""Tk modifier masks differ by window system, including Num Lock on Windows."""


def blocks_shortcut(state, window_system):
    # Tk/Windows: Mod1 (0x8) is Num Lock, whereas Alt uses ALT_MASK.
    # Do not reject Num Lock, Caps Lock, Scroll Lock, or extended cursor keys.
    alt_mask = 0x20000 if window_system == 'win32' else 0x8
    return bool(state & (0x4 | alt_mask))
