"""
Nuke menu.py - VfxPipe Menu Setup

This file is loaded by Nuke after init.py to set up menus.
Currently minimal - menu entries will be registered by VfxPipe tools.

Installation:
    Set NUKE_PATH environment variable to include the DCC_plugins/nuke directory,
    or copy/symlink this file to your ~/.nuke directory.
"""

# Menu setup is handled by VfxPipe.nuke.startup.init
# Individual tools will register their menu entries during initialization
# This file is kept minimal to maintain flexibility

print("[VfxPipe] menu.py loaded - menu entries registered by tools")
