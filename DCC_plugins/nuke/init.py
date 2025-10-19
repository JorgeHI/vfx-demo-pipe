"""
Nuke init.py - VfxPipe Bootstrap

This file is loaded by Nuke on startup (placed in ~/.nuke or NUKE_PATH).
It performs minimal bootstrapping: adds the VfxPipe path to sys.path and
triggers the main initialization.

Installation:
    Set NUKE_PATH environment variable to include the DCC_plugins/nuke directory,
    or copy/symlink this file to your ~/.nuke directory.
"""

import sys
from pathlib import Path


def bootstrap_vfxpipe():
    """Add VfxPipe to sys.path and trigger initialization."""
    # Get the root directory (two levels up from this file)
    # DCC_plugins/nuke/init.py -> DCC_plugins/nuke -> DCC_plugins -> root
    plugin_dir = Path(__file__).parent.resolve()
    root_dir = plugin_dir.parent.parent

    # Add root to sys.path if not already present
    root_path = str(root_dir)
    if root_path not in sys.path:
        sys.path.insert(0, root_path)

    # Import and run VfxPipe Nuke startup
    try:
        from VfxPipe.nuke.startup import init
        init.initialize()
    except Exception as e:
        print(f"[VfxPipe] Failed to initialize: {e}")
        import traceback
        traceback.print_exc()


# Execute bootstrap on import
bootstrap_vfxpipe()
