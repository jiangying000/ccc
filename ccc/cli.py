#!/usr/bin/env python3
"""
CLI entry point for CCC
"""

import sys
from .extractor import main

def ccc():
    """Main entry point - always interactive session selector"""
    sys.argv = ['ccc']
    main()

if __name__ == '__main__':
    main()
