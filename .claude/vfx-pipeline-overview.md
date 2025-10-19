# VfxPipe - Project Overview for Claude

## Project Purpose

This is a **demo VFX pipeline** created specifically for demonstrating and testing pipeline tools. The primary use case is to provide a realistic VFX pipeline environment for showcasing tools like error reporting systems, ticket submission workflows, and DCC integration patterns.

**This is NOT a production pipeline** - it's intentionally simplified to serve as a testing ground and demonstration platform.

## Architecture Overview

### Two-Tier Structure

The project uses a two-tier architecture to separate concerns:

1. **DCC_plugins/** - Minimal bootstrap layer
   - Contains only the bare minimum code needed by each DCC application
   - Handles path setup and imports the main VfxPipe package
   - Lives in the DCC's configuration directory (e.g., `~/.nuke` or `NUKE_PATH`)

2. **VfxPipe/** - Main pipeline package
   - Contains all actual pipeline logic
   - Organized by DCC application (nuke, maya, etc.)
   - Can be version controlled and deployed independently

### Why This Structure?

This separation allows:
- Easy deployment: Only VfxPipe needs to be updated, DCC_plugins stays minimal
- Version control: The main package can be easily managed in git
- Testing: VfxPipe can be tested outside of DCC applications
- Multi-DCC support: Same pattern works for Maya, Houdini, etc.

## Directory Breakdown

### VfxPipe/nuke/

```
nuke/
├── tools/       # Individual tool implementations
├── startup/     # Initialization and bootstrapping logic
└── widgets/     # Custom UI components (panels, dialogs, etc.)
```

**tools/** - Each tool is a separate Python module that implements a `register()` function. The startup system automatically discovers and loads all tools.

**startup/init.py** - The main initialization orchestrator that:
1. Validates the environment (Python version, Nuke availability, paths)
2. Discovers tools in the `tools/` directory
3. Calls each tool's `register()` function
4. Sets up the VfxPipe menu in Nuke

**widgets/** - Reusable UI components specific to Nuke (built with Nuke's PySide/PyQt)

### VfxPipe/utils/ and VfxPipe/widgets/

These are for shared code that works across multiple DCC applications:
- **utils/** - Helper functions, file I/O, path handling, etc.
- **widgets/** - DCC-agnostic UI components (if using a common framework)

### DCC_plugins/nuke/

Contains exactly two files:

**init.py** - Nuke loads this on startup. It:
1. Calculates the path to the VfxPipe package
2. Adds it to `sys.path`
3. Imports and calls `VfxPipe.nuke.startup.init.initialize()`

**menu.py** - Nuke loads this after init.py. Currently minimal since menu setup is handled by VfxPipe itself.

## Tool Development Pattern

To add a new tool to the pipeline:

1. Create `VfxPipe/nuke/tools/my_new_tool.py`
2. Implement the required interface:

```python
def register():
    """Called by startup system - returns tool metadata"""
    return {
        'menu_name': 'My Tool Name',
        'action': run_tool  # Function to call when menu is clicked
    }

def run_tool():
    """Main tool implementation"""
    # Tool logic here
    pass
```

3. Restart Nuke - the tool is automatically discovered and added to the menu

## Key Design Principles

1. **Auto-discovery** - Tools are automatically found and loaded, no manual registration required
2. **Minimal bootstrap** - DCC plugin files are kept as simple as possible
3. **Extensible** - Easy to add new tools without modifying core infrastructure
4. **DCC-agnostic core** - Structure can be replicated for Maya, Houdini, etc.
5. **Error resilient** - If one tool fails to load, others continue working

## Current State

As of now, the project has:
- ✅ Complete directory structure
- ✅ All `__init__.py` files for proper Python packaging
- ✅ Bootstrap files for Nuke (init.py, menu.py)
- ✅ Full startup/initialization framework
- ✅ Tool auto-discovery system
- ✅ Menu setup system
- ❌ No actual tools implemented yet (next step)

## Next Steps

The next phase is to add demo tools to `VfxPipe/nuke/tools/`. These could include:
- Error reporting tool (submits tickets when errors occur)
- Scene info tool (displays current scene metadata)
- Asset browser (demo of pipeline integration)
- Render submitter (demo of farm integration)

Each tool should be simple enough to serve as a demo but realistic enough to showcase actual pipeline patterns.

## Integration Points

This pipeline is designed to integrate with:
- **Error reporting systems** - Tools can catch and report errors
- **Ticket submission systems** - Example: the error reporter you're implementing
- **Asset management** - Can be extended to show asset workflows
- **Render farm integration** - Demo render submission patterns

## Important Notes for Development

- Always test that tools gracefully handle Nuke not being available (for unit testing)
- Keep individual tools focused and simple - this is a demo, not production
- Use proper error handling so one broken tool doesn't break the entire pipeline
- Include logging/print statements so initialization can be debugged
- Tools should be self-contained with minimal dependencies on each other
