"""
Auto Track Tool - Automated Camera Tracking for Nuke

Provides automated camera tracking functionality with recursive solve refinement.
Integrates with the Auto Track Widget for user configuration.
"""

import nuke
import nukescripts
from VfxPipe.utils.host import getPySideVersion

# Dynamically import correct PySide version based on DCC
_pyside_version = getPySideVersion()

try:
    if _pyside_version == 2:
        from PySide2 import QtCore
    else:
        from PySide6 import QtCore
except ImportError as e:
    raise ImportError(
        f"PySide{_pyside_version} is required for this DCC but not available. "
        f"Please install PySide{_pyside_version}. Error: {e}"
    )


class TrackingWorker(QtCore.QThread):
    """
    Worker thread for camera tracking operations.

    Runs tracking operations in a separate thread to keep UI responsive.
    """

    # Signals for progress updates
    progress_update = QtCore.Signal(str, float, str)  # message, percentage, detail
    tracking_complete = QtCore.Signal(bool, str)  # success, message
    error_occurred = QtCore.Signal(str, str)  # title, message

    def __init__(self, params):
        super(TrackingWorker, self).__init__()
        self.params = params
        self.cancelled = False

    def run(self):
        """Execute the tracking process."""
        try:
            nodes = self.params['nodes']
            total_nodes = len(nodes)

            for idx, node_name in enumerate(nodes):
                if self.cancelled:
                    self.tracking_complete.emit(False, "Tracking cancelled by user")
                    return

                # Calculate progress
                base_progress = (idx / total_nodes) * 100

                # Get node
                try:
                    node = nuke.toNode(node_name)
                    if not node:
                        raise Exception(f"Node '{node_name}' not found")
                except Exception as e:
                    self.error_occurred.emit("Node Error", str(e))
                    return

                # Process this node
                self.progress_update.emit(
                    f"Processing {node_name} ({idx + 1}/{total_nodes})",
                    base_progress,
                    "Preparing to track..."
                )

                try:
                    self._process_camera_tracker(
                        node,
                        node_name,
                        base_progress,
                        100.0 / total_nodes
                    )
                except Exception as e:
                    self.error_occurred.emit(
                        f"Error processing {node_name}",
                        f"Failed to process camera tracker:\n\n{str(e)}"
                    )
                    return

            # Complete
            self.tracking_complete.emit(
                True,
                f"Successfully processed {total_nodes} camera tracker(s)"
            )

        except Exception as e:
            self.error_occurred.emit("Tracking Error", f"Unexpected error:\n\n{str(e)}")

    def _process_camera_tracker(self, node, node_name, base_progress, progress_range):
        """
        Process a single camera tracker node.

        Args:
            node: CameraTracker node
            node_name: Name of the node
            base_progress: Starting progress percentage
            progress_range: Range of progress this node represents
        """
        # Show control panel
        node.showControlPanel()

        # Get current plate name
        try:
            plate_name = nuke.tcl(f"full_name [topnode {node.name()}]")
        except:
            plate_name = node_name

        # Track Features
        if self.cancelled:
            return

        self.progress_update.emit(
            f"Tracking {node_name}",
            base_progress + (progress_range * 0.2),
            f"Tracking features on plate: {plate_name}"
        )
        node["trackFeatures"].execute()

        # Solve Camera
        if self.cancelled:
            return

        self.progress_update.emit(
            f"Solving {node_name}",
            base_progress + (progress_range * 0.4),
            f"Solving camera for plate: {plate_name}"
        )
        node["solveCamera"].execute()

        # Recursive update solve
        if self.cancelled:
            return

        self.progress_update.emit(
            f"Refining {node_name}",
            base_progress + (progress_range * 0.5),
            f"Starting recursive solve refinement (target RMSE: {self.params['controlError']})"
        )

        self._update_solve_recursive(
            node,
            node_name,
            base_progress + (progress_range * 0.5),
            progress_range * 0.3
        )

        # Create Camera
        if self.cancelled:
            return

        self.progress_update.emit(
            f"Creating camera for {node_name}",
            base_progress + (progress_range * 0.9),
            f"Generating camera node: {self.params['camera_prefix']}{plate_name}"
        )

        # Store current cameras to find the new one
        cameras_before = set(nuke.allNodes('Camera3'))

        # Create camera using the enhanced function
        camera_node = self._create_camera(node)

        # Find and rename the new camera
        cameras_after = set(nuke.allNodes('Camera3'))
        new_cameras = cameras_after - cameras_before

        if new_cameras:
            camera_node = list(new_cameras)[0]
            camera_node.setName(f"{self.params['camera_prefix']}{plate_name}")
            self.progress_update.emit(
                f"Completed {node_name}",
                base_progress + progress_range,
                f"Created camera: {camera_node.name()}"
            )

    def _create_camera(self, solver):
        """
        Create a camera node based on the projection calculated by the solver.

        Args:
            solver: CameraTracker node

        Returns:
            Created Camera node
        """
        x = solver.xpos()
        y = solver.ypos()
        w = solver.screenWidth()
        h = solver.screenHeight()
        m = int(x + w/2)
        numviews = len(nuke.views())

        # Use link setting from params
        link = self.params['link_output']

        camera = nuke.createNode('Camera', '', False)
        camera.setInput(0, None)
        camera.setXYpos(m - int(camera.screenWidth()/2), y + w)

        if link:
            # Link with expressions
            camera.knob("focal").setExpression(solver.name() + ".focalLength")
            camera.knob("haperture").setExpression(solver.name() + ".aperture.x")
            camera.knob("vaperture").setExpression(solver.name() + ".aperture.y")
            camera.knob("translate").setExpression(solver.name() + ".camTranslate")
            camera.knob("rotate").setExpression(solver.name() + ".camRotate")
            camera.knob("win_translate").setExpression(solver.name() + ".windowTranslate")
            camera.knob("win_scale").setExpression(solver.name() + ".windowScale")
        else:
            # Bake values
            camera.knob("focal").fromScript(solver.knob("focalLength").toScript(False))
            camera.knob("translate").fromScript(solver.knob("camTranslate").toScript(False))
            camera.knob("rotate").fromScript(solver.knob("camRotate").toScript(False))
            camera.knob("win_translate").fromScript(solver.knob("windowTranslate").toScript(False))
            camera.knob("win_scale").fromScript(solver.knob("windowScale").toScript(False))
            for i in range(numviews):
                camera.knob("haperture").setValue(solver.knob("aperture").getValue(0, i+1), 0, 0, i+1)
                camera.knob("vaperture").setValue(solver.knob("aperture").getValue(1, i+1), 0, 0, i+1)

        return camera

    def _update_solve(self, cameraTracker):
        """
        Update the solve for a camera tracker.

        Args:
            cameraTracker: CameraTracker node
        """
        refFrames = [cameraTracker['trackStart'].value(), cameraTracker['trackStop'].value()]
        selFrameKnob = cameraTracker.knob('selectedFrames')
        selFrameKnob.clearAnimated()
        selFrameKnob.setAnimated()

        for frame in refFrames:
            selFrameKnob.setValueAt(frame, frame)

        cameraTracker.knob("doUpdateSolve").execute()

    def _update_solve_recursive(self, node, node_name, base_progress, progress_range):
        """
        Recursively update solve to reduce error.

        Args:
            node: CameraTracker node
            node_name: Name of the node
            base_progress: Starting progress percentage
            progress_range: Range of progress this represents
        """
        params = self.params
        minLen = params['minLen']
        maxTrackError = params['maxTrackError']
        maxError = params['maxError']
        controlError = params['controlError']
        max_iter = params['max_iter']

        iteration = 0

        while node['solveRMSE'].value() >= controlError and iteration < max_iter:
            if self.cancelled:
                return

            current_rmse = node['solveRMSE'].value()

            # Update thresholds
            node['minLengthThreshold'].setValue(minLen)
            node['maxRMSEThreshold'].setValue(maxTrackError)
            node['maxErrorThreshold'].setValue(maxError)

            # Delete rejected tracks
            node['deleteRejectedTracks'].setValue(
                "cameraTracker = nuke.thisNode()\n"
                "cameraTracker['proceedWithUpdate'].setValue(True)"
            )
            node['deleteRejectedTracks'].execute()

            # Delete invalid tracks
            node['deleteInvalidTracks'].setValue(
                "cameraTracker = nuke.thisNode()\n"
                "cameraTracker['proceedWithUpdate'].setValue(True)"
            )
            node['deleteInvalidTracks'].execute()

            # Update solve
            self._update_solve(node)

            new_rmse = node['solveRMSE'].value()

            # Update progress
            iter_progress = base_progress + (iteration / max_iter) * progress_range
            detail = (
                f"Iteration {iteration + 1}/{max_iter} | "
                f"RMSE: {current_rmse:.4f} → {new_rmse:.4f} | "
                f"Target: {controlError:.4f} | "
                f"MinLen: {minLen}, MaxError: {maxError:.2f}"
            )

            self.progress_update.emit(
                f"Refining {node_name}",
                iter_progress,
                detail
            )

            # Adjust parameters for next iteration
            minLen += 1
            maxTrackError -= 0.25
            maxError -= 0.25
            iteration += 1

        # Final status
        final_rmse = node['solveRMSE'].value()
        final_detail = (
            f"Refinement complete after {iteration} iteration(s) | "
            f"Final RMSE: {final_rmse:.4f}"
        )

        self.progress_update.emit(
            f"Refining {node_name}",
            base_progress + progress_range,
            final_detail
        )

    def cancel(self):
        """Cancel the tracking operation."""
        self.cancelled = True


# Global reference to widget and worker
_widget = None
_worker = None


def show_auto_track_widget():
    """
    Show the Auto Track widget.

    This is the main entry point called from the VfxPipe menu.
    """
    global _widget, _worker

    # Import widget
    from VfxPipe.nuke.widgets.auto_track_widget import AutoTrackWidget

    # Create widget if needed
    if _widget is None:
        _widget = AutoTrackWidget()

        # Connect signals
        _widget.start_tracking.connect(_on_start_tracking)
        _widget.cancel_tracking.connect(_on_cancel_tracking)

    # Show widget
    _widget.show()
    _widget.raise_()
    _widget.activateWindow()


def _on_start_tracking(params):
    """
    Handle start tracking signal from widget.

    Args:
        params: Dictionary of tracking parameters
    """
    global _worker

    # Create and start worker thread
    _worker = TrackingWorker(params)

    # Connect worker signals to widget
    _worker.progress_update.connect(_widget.update_status)
    _worker.tracking_complete.connect(_widget.tracking_complete)
    _worker.error_occurred.connect(_widget.show_error)

    # Start processing
    _worker.start()


def _on_cancel_tracking():
    """Handle cancel tracking signal from widget."""
    global _worker

    if _worker and _worker.isRunning():
        _worker.cancel()


def register():
    """
    Register the Auto Track tool with VfxPipe.

    Returns:
        Dictionary with tool metadata for menu registration
    """
    return {
        'menu_name': 'Auto Track',
        'action': show_auto_track_widget
    }
