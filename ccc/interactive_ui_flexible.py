#!/usr/bin/env python3
"""
Flexible Interactive UI (CCC) - copied from original with minimal rename
"""

import os
CCC_MODE = os.environ.get('CCC_MODE', 'SAFE').upper()

TERMIOS_AVAILABLE = False
try:
    import termios  # noqa: F401
    import tty  # noqa: F401
    TERMIOS_AVAILABLE = True
except Exception:
    TERMIOS_AVAILABLE = False

class InteractiveSessionSelectorFlexible:
    pass  # Keep placeholder; original flexible UI is not referenced directly here.
