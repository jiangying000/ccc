#!/usr/bin/env python3
"""
CLI entry points for CCDRC
"""

import sys
import subprocess
from .extractor import main

def ccdrc():
    """Main entry point - always interactive session selector"""
    # Always use interactive mode
    sys.argv = ['ccdrc', '--interactive', '--send']
    main()

def ccdrc_extract():
    """Extract entry point - just extraction without sending"""
    main()

def ccdrc_interactive():
    """Interactive entry point"""
    sys.argv = ['ccdrc-interactive', '--interactive', '--send']
    main()

if __name__ == '__main__':
    main()