# VfxPipe - Demo VFX Pipeline

A demonstration VFX pipeline structure designed for showcasing pipeline tools, error reporting systems, and integration patterns with DCC applications.

## Purpose

This project serves as a minimal, working VFX pipeline that can be used to:
- Demonstrate pipeline tool integration with DCC applications
- Showcase error reporting and ticket submission workflows
- Provide a realistic testing environment for pipeline development tools
- Serve as a template for building production pipelines

## Project Structure

```
vfx-demo-pipe/
├── VfxPipe/                    # Main pipeline package
│   ├── __init__.py
│   ├── nuke/                   # Nuke-specific integration
│   │   ├── __init__.py
│   │   ├── tools/              # Nuke tools
│   │   │   └── __init__.py
│   │   ├── startup/            # Initialization scripts
│   │   │   ├── __init__.py
│   │   │   └── init.py         # Main startup logic
│   │   └── widgets/            # Nuke UI widgets
│   │       └── __init__.py
│   ├── utils/                  # Shared utilities
│   │   └── __init__.py
│   └── widgets/                # Common widgets
│       └── __init__.py
│
├── DCC_plugins/                # DCC bootstrap files
│   └── nuke/
│       ├── init.py             # Nuke init bootstrap
│       └── menu.py             # Nuke menu bootstrap
│
└── README.md
```

## Installation

### For Nuke

1. Set the `NUKE_PATH` environment variable to include the `DCC_plugins/nuke` directory:

```bash
export NUKE_PATH=/path/to/vfx-demo-pipe/DCC_plugins/nuke:$NUKE_PATH
```

2. Alternatively, copy or symlink the files to your `~/.nuke` directory:

```bash
ln -s /path/to/vfx-demo-pipe/DCC_plugins/nuke/init.py ~/.nuke/init.py
ln -s /path/to/vfx-demo-pipe/DCC_plugins/nuke/menu.py ~/.nuke/menu.py
```

3. Launch Nuke - you should see VfxPipe initialization messages in the console

## Architecture

### Bootstrap Process

1. **DCC_plugins/nuke/init.py** - Minimal bootstrap
   - Adds VfxPipe to `sys.path`
   - Imports and calls `VfxPipe.nuke.startup.init.initialize()`

2. **VfxPipe/nuke/startup/init.py** - Main initialization
   - Validates environment
   - Discovers and registers tools from `VfxPipe/nuke/tools/`
   - Sets up menus in Nuke

3. **Tools** - Auto-discovered modules
   - Tools implement a `register()` function
   - Return metadata including menu entries and actions
   - Automatically integrated during startup

### Adding Tools

To add a new tool:

1. Create a Python file in `VfxPipe/nuke/tools/` (e.g., `my_tool.py`)
2. Implement a `register()` function that returns tool metadata:

```python
def register():
    """Register this tool with VfxPipe."""
    return {
        'menu_name': 'My Tool',
        'action': my_tool_action
    }

def my_tool_action():
    """Tool implementation."""
    import nuke
    nuke.message("Hello from My Tool!")
```

3. Restart Nuke - the tool will be automatically discovered and added to the VfxPipe menu

## Development

### Requirements

- Python 3.7+
- Nuke (for Nuke integration)

### Future DCC Support

The structure is designed to be extended with additional DCC applications:

```
VfxPipe/
├── maya/
├── houdini/
└── ...

DCC_plugins/
├── maya/
├── houdini/
└── ...
```

## Use Cases

This demo pipeline is ideal for:

- Testing pipeline tool development frameworks
- Demonstrating error reporting and logging systems
- Training and educational purposes
- Prototyping pipeline features before production implementation

## Version

Current version: 0.1.0

## License

Demo project - use as needed for development and testing purposes.
