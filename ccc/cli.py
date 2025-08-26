#!/usr/bin/env python3
"""
CLI entry point for CCC
"""

import sys
from .extractor import main

def ccc():
    """Console entry point.

    Preserve command-line args so flags like --help/--tokens work.
    Delegates to extractor.main() which handles argument parsing
    and the interactive UI.
    """
    # Do not overwrite sys.argv; pass through whatever user supplied
    main()

if __name__ == '__main__':
    main()
