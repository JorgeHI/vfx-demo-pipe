"""
VfxPipe Nuke Initialization

Main initialization module that sets up the VfxPipe environment within Nuke.
This module handles:
- Environment validation
- Tool discovery and registration
- Menu setup
- Logging configuration
"""

import sys
from pathlib import Path
from typing import List, Dict, Any


# Track initialization state
_initialized = False
_registered_tools = []


def initialize():
    """
    Main initialization function called from DCC_plugins/nuke/init.py

    This function orchestrates the entire startup sequence for VfxPipe in Nuke.
    """
    global _initialized

    if _initialized:
        print("[VfxPipe] Already initialized, skipping...")
        return

    print("[VfxPipe] Initializing VfxPipe for Nuke...")

    # Run initialization steps
    validate_environment()
    discover_and_register_tools()
    setup_menus()

    _initialized = True
    print("[VfxPipe] Initialization complete!")


def validate_environment():
    """
    Validate that the Nuke environment is properly set up.

    Checks:
    - Nuke is available
    - Required Python version
    - VfxPipe paths are accessible
    """
    print("[VfxPipe] Validating environment...")

    # Check Python version
    if sys.version_info < (3, 7):
        print("[VfxPipe] WARNING: Python 3.7+ recommended")

    # Check if nuke module is available
    try:
        import nuke
        print(f"[VfxPipe] Nuke version: {nuke.NUKE_VERSION_STRING}")
    except ImportError:
        print("[VfxPipe] WARNING: Nuke module not available (may be expected in some contexts)")

    # Verify VfxPipe package structure
    vfxpipe_root = Path(__file__).parent.parent.parent
    required_dirs = ['nuke/tools', 'nuke/widgets', 'utils']

    for dir_path in required_dirs:
        full_path = vfxpipe_root / dir_path
        if not full_path.exists():
            print(f"[VfxPipe] WARNING: Missing directory: {dir_path}")

    print("[VfxPipe] Environment validation complete")


def discover_and_register_tools():
    """
    Discover and register all available VfxPipe tools.

    Scans the VfxPipe/nuke/tools directory for tool modules and registers them.
    Tools should implement a register() function to be auto-loaded.
    """
    global _registered_tools

    print("[VfxPipe] Discovering tools...")

    tools_dir = Path(__file__).parent.parent / "tools"

    if not tools_dir.exists():
        print("[VfxPipe] No tools directory found")
        return

    # Find all Python modules in tools directory (excluding __init__.py)
    tool_modules = [
        f.stem for f in tools_dir.glob("*.py")
        if f.is_file() and f.stem != "__init__"
    ]

    if not tool_modules:
        print("[VfxPipe] No tools found in tools directory")
        return

    # Import and register each tool
    for tool_name in tool_modules:
        try:
            print(f"[VfxPipe] Loading tool: {tool_name}")
            module = __import__(
                f"VfxPipe.nuke.tools.{tool_name}",
                fromlist=[tool_name]
            )

            # Check if module has a register function
            if hasattr(module, 'register'):
                tool_info = module.register()
                _registered_tools.append({
                    'name': tool_name,
                    'module': module,
                    'info': tool_info
                })
                print(f"[VfxPipe] Registered tool: {tool_name}")
            else:
                print(f"[VfxPipe] WARNING: Tool {tool_name} has no register() function")

        except Exception as e:
            print(f"[VfxPipe] ERROR loading tool {tool_name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"[VfxPipe] Registered {len(_registered_tools)} tool(s)")


def setup_menus():
    """
    Set up VfxPipe menu entries in Nuke.

    Creates the main VfxPipe menu and adds entries for registered tools.
    """
    print("[VfxPipe] Setting up menus...")

    try:
        import nuke

        # Get or create the VfxPipe menu in the main menu bar
        menubar = nuke.menu("Nuke")
        vfxpipe_menu = menubar.addMenu("VfxPipe")

        # Add menu entries for each registered tool
        for tool in _registered_tools:
            tool_info = tool.get('info', {})

            if not tool_info:
                continue

            menu_name = tool_info.get('menu_name', tool['name'])
            menu_action = tool_info.get('action')

            if menu_action:
                vfxpipe_menu.addCommand(menu_name, menu_action)
                print(f"[VfxPipe] Added menu entry: {menu_name}")

        # Add separator and about entry
        if _registered_tools:
            vfxpipe_menu.addSeparator()

        vfxpipe_menu.addCommand("About VfxPipe", show_about)

        print("[VfxPipe] Menu setup complete")

    except ImportError:
        print("[VfxPipe] Nuke not available, skipping menu setup")
    except Exception as e:
        print(f"[VfxPipe] ERROR setting up menus: {e}")
        import traceback
        traceback.print_exc()


def show_about():
    """Display information about VfxPipe."""
    try:
        import nuke
        from VfxPipe import __version__

        message = f"""VfxPipe Demo Pipeline
Version: {__version__}

A demonstration VFX pipeline for showcasing
pipeline tools and integration patterns.

Registered Tools: {len(_registered_tools)}
"""
        nuke.message(message)
    except Exception as e:
        print(f"[VfxPipe] Error showing about: {e}")


def get_registered_tools() -> List[Dict[str, Any]]:
    """
    Get list of registered tools.

    Returns:
        List of dictionaries containing tool information
    """
    return _registered_tools.copy()


def is_initialized() -> bool:
    """
    Check if VfxPipe has been initialized.

    Returns:
        True if initialized, False otherwise
    """
    return _initialized
