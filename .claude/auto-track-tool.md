# Auto Track Tool - Implementation Reference

## Overview

The Auto Track tool is the first demo tool implemented in the VfxPipe pipeline. It provides automated camera tracking for Nuke with a Qt-based interface for configuration and progress monitoring.

## Files

### VfxPipe/nuke/tools/auto_track.py
Main tool implementation containing:
- **TrackingWorker** - QThread class that runs tracking operations in background
- **Camera creation logic** - Based on user's provided code with link/bake options
- **Recursive solve refinement** - Iteratively reduces RMSE by adjusting thresholds
- **register()** - Returns menu metadata for VfxPipe integration

### VfxPipe/nuke/widgets/auto_track_widget.py
Qt interface providing:
- Node selection table with checkboxes
- Parameter configuration UI
- Progress bar with detailed status
- Error handling dialogs

## User Workflow

1. **Select nodes** - Select one or more CameraTracker nodes in Nuke
2. **Open tool** - Menu: VfxPipe > Auto Track
3. **Review nodes** - Widget shows selected nodes, can check/uncheck which to process
4. **Configure** - Set tracking parameters (or use defaults)
5. **Track** - Click "Track Cameras" button
6. **Monitor** - Watch detailed progress for each node
7. **Complete** - Camera nodes are created with custom names

## Parameters

### Recursive Tracking Parameters
- **Min Track Length** (default: 3) - Minimum track length threshold
- **Max Track Error** (default: 4.0) - Maximum RMSE threshold for tracks
- **Max Error** (default: 4.0) - Maximum error threshold
- **Control Error** (default: 1.0) - Target RMSE to achieve
- **Max Iterations** (default: 5) - Maximum number of refinement iterations

### Camera Options
- **Camera Name Prefix** (default: "cam_") - Prefix for generated camera names
- **Link Camera Output** (checkbox) - If checked: uses expressions to link to solver, if unchecked: bakes values

## Processing Steps (Per Node)

1. **Track Features** - Executes feature tracking on the plate
2. **Solve Camera** - Calculates initial camera solve
3. **Recursive Refinement** - Iteratively improves solve by:
   - Deleting rejected tracks
   - Deleting invalid tracks
   - Updating solve
   - Adjusting thresholds (minLen++, maxError-=0.25, etc.)
   - Repeating until RMSE < controlError or max_iter reached
4. **Create Camera** - Generates camera node with name: `{prefix}{plate_name}`

## Progress Updates

The UI shows detailed progress including:
- Current node being processed (1/N)
- Current step (tracking/solving/refining/creating)
- Iteration count during refinement
- RMSE values (before → after each iteration)
- Current threshold values
- Final results

## Technical Details

### Threading
- Uses QThread to run tracking operations in background
- Keeps UI responsive during long operations
- Signals/slots for communication between worker and UI

### Error Handling
- Stop-on-first-error behavior
- Shows detailed error dialog with node name and exception
- Cancel functionality allows user to abort processing

### Camera Creation
Based on user's original code, with enhancements:
- Supports both linked (expression-based) and baked camera output
- Proper positioning in node graph
- Multi-view support
- Automatic naming based on plate name

## Integration with VfxPipe

The tool is automatically discovered and registered by the startup system:
1. VfxPipe/nuke/startup/init.py scans tools/ directory
2. Finds auto_track.py
3. Calls register() function
4. Adds menu entry: VfxPipe > Auto Track
5. Clicking menu calls show_auto_track_widget()

## Future Enhancements

Potential improvements for this demo tool:
- Batch processing with continue-on-error option
- Save/load parameter presets
- Export tracking data/reports
- Integration with error reporting system (submit tickets on failures)
- Add more camera creation options (lens distortion, etc.)
- Support for track range customization per node

## Code References

Key functions:
- `auto_track.py:show_auto_track_widget()` - Main entry point
- `auto_track.py:TrackingWorker._process_camera_tracker()` - Per-node processing
- `auto_track.py:TrackingWorker._update_solve_recursive()` - Recursive refinement
- `auto_track_widget.py:AutoTrackWidget.refresh_nodes()` - Populate node list
- `auto_track_widget.py:AutoTrackWidget.get_parameters()` - Gather user inputs

## Testing Notes

To test this tool:
1. Create a CameraTracker node in Nuke connected to a plate
2. Select the CameraTracker node
3. Open VfxPipe > Auto Track
4. Leave default parameters or adjust as needed
5. Click "Track Cameras"
6. Verify progress updates appear
7. Check that camera node is created with correct name
8. Verify camera has proper focal length and animation

## Usage as Demo

This tool serves as an excellent demo for:
- VfxPipe tool structure and registration
- Qt UI integration in Nuke
- Background processing with progress updates
- Error handling and user feedback
- Practical pipeline automation

It's complex enough to be realistic but simple enough to understand and modify.
