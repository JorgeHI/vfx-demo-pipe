"""
Host DCC Detection and Version Utilities

Provides functions to detect the current DCC application and determine
appropriate Qt/PySide versions for compatibility across different DCC versions.
"""


def getDcc():
    """
    Detect the current DCC application.

    Returns:
        str or None: DCC name ('nuke', 'maya', 'houdini', etc.) or None if standalone

    Examples:
        >>> dcc = getDcc()
        >>> if dcc == 'nuke':
        ...     print("Running in Nuke")
    """
    # Try Nuke
    try:
        import nuke
        return "nuke"
    except ImportError:
        pass

    # Try Maya
    try:
        import maya.cmds
        return "maya"
    except ImportError:
        pass

    # Try Houdini
    try:
        import hou
        return "houdini"
    except ImportError:
        pass

    # Try Blender
    try:
        import bpy
        return "blender"
    except ImportError:
        pass

    # No DCC detected - standalone Python
    return None


def getPySideVersion(dcc=None):
    """
    Get the appropriate PySide version (2 or 6) for the current DCC.

    Different DCC applications and versions require different PySide versions:
    - Nuke 15 and older: PySide2
    - Nuke 16 and newer: PySide6
    - Maya 2025 and older: PySide2
    - Other/Unknown: PySide6 (default)

    Args:
        dcc (str, optional): DCC name. If None, will auto-detect using getDcc()

    Returns:
        int: PySide version (2 or 6)

    Raises:
        RuntimeError: If DCC is detected but version cannot be determined

    Examples:
        >>> version = getPySideVersion()
        >>> if version == 2:
        ...     from PySide2 import QtWidgets
        ... else:
        ...     from PySide6 import QtWidgets
    """
    # Auto-detect DCC if not provided
    if dcc is None:
        dcc = getDcc()

    # Handle Nuke
    if dcc == "nuke":
        try:
            import nuke

            # Get Nuke major version
            # NUKE_VERSION_MAJOR is available in Nuke 11.2+
            if hasattr(nuke, 'NUKE_VERSION_MAJOR'):
                major_version = nuke.NUKE_VERSION_MAJOR
            else:
                # Fallback: parse from NUKE_VERSION_STRING (e.g., "15.1v3")
                version_string = nuke.NUKE_VERSION_STRING
                major_version = int(version_string.split('.')[0])

            # Nuke 16+ uses PySide6, older versions use PySide2
            if major_version >= 16:
                return 6
            else:
                return 2

        except Exception as e:
            raise RuntimeError(f"Failed to detect Nuke version: {e}")

    # Handle Maya
    elif dcc == "maya":
        try:
            import maya.cmds as cmds

            # Get Maya version (returns string like "2024")
            maya_version = int(cmds.about(version=True))

            # Maya 2025+ uses PySide6, older versions use PySide2
            if maya_version >= 2025:
                return 6
            else:
                return 2

        except Exception as e:
            raise RuntimeError(f"Failed to detect Maya version: {e}")

    # Handle Houdini
    elif dcc == "houdini":
        try:
            import hou

            # Get Houdini version tuple (major, minor, patch)
            version_tuple = hou.applicationVersion()
            major_version = version_tuple[0]

            # Houdini 20+ uses PySide6, older versions use PySide2
            if major_version >= 20:
                return 6
            else:
                return 2

        except Exception as e:
            raise RuntimeError(f"Failed to detect Houdini version: {e}")

    # For unknown DCCs or standalone Python, default to PySide6
    else:
        return 6


def get_nuke_version():
    """
    Get the Nuke version as a tuple (major, minor, patch).

    Returns:
        tuple or None: (major, minor, patch) or None if not in Nuke

    Examples:
        >>> version = get_nuke_version()
        >>> if version and version[0] >= 16:
        ...     print("Nuke 16 or newer")
    """
    try:
        import nuke

        if hasattr(nuke, 'NUKE_VERSION_MAJOR'):
            major = nuke.NUKE_VERSION_MAJOR
            minor = nuke.NUKE_VERSION_MINOR if hasattr(nuke, 'NUKE_VERSION_MINOR') else 0
            patch = nuke.NUKE_VERSION_RELEASE if hasattr(nuke, 'NUKE_VERSION_RELEASE') else 0
            return (major, minor, patch)
        else:
            # Fallback: parse from NUKE_VERSION_STRING
            version_string = nuke.NUKE_VERSION_STRING
            # Format: "15.1v3" -> (15, 1, 3)
            parts = version_string.replace('v', '.').split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return (major, minor, patch)

    except ImportError:
        return None


def is_nuke_16_or_newer():
    """
    Check if running in Nuke 16 or newer.

    Returns:
        bool: True if Nuke 16+, False otherwise

    Examples:
        >>> if is_nuke_16_or_newer():
        ...     from PySide6 import QtWidgets
        ... else:
        ...     from PySide2 import QtWidgets
    """
    version = get_nuke_version()
    return version is not None and version[0] >= 16


# Convenience constants
DCC_NAME = getDcc()
PYSIDE_VERSION = getPySideVersion()


if __name__ == "__main__":
    # Test/debug output
    print(f"Detected DCC: {getDcc()}")
    print(f"PySide Version: {getPySideVersion()}")

    if getDcc() == "nuke":
        print(f"Nuke Version: {get_nuke_version()}")
        print(f"Is Nuke 16+: {is_nuke_16_or_newer()}")
