"""
Auto Track Tool - Automated Camera Tracking for Nuke

Provides automated camera tracking functionality with recursive solve refinement.
Integrates with the Auto Track Widget for user configuration.
"""

import nuke
import nukescripts
import time
from VfxPipe.utils.host import getPySideVersion
from VfxPipe.utils.logger import getLogger

# Initialize logger
logger = getLogger("AutoTrack")

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
        logger.info("=" * 60)
        logger.info("AUTO TRACK PROCESS STARTED")
        logger.info("=" * 60)

        try:
            nodes = self.params['nodes']
            total_nodes = len(nodes)
            logger.info(f"Processing {total_nodes} CameraTracker node(s): {nodes}")
            logger.info(f"Parameters: {self.params}")

            for idx, node_name in enumerate(nodes):
                if self.cancelled:
                    logger.warning("Tracking cancelled by user")
                    self.tracking_complete.emit(False, "Tracking cancelled by user")
                    return

                # Calculate progress
                base_progress = (idx / total_nodes) * 100
                logger.info(f"\n{'=' * 60}")
                logger.info(f"Processing node {idx + 1}/{total_nodes}: {node_name}")
                logger.info(f"{'=' * 60}")

                # Get node
                try:
                    node = nuke.toNode(node_name)
                    if not node:
                        raise Exception(f"Node '{node_name}' not found")
                    logger.info(f"Node found: {node.Class()} - {node_name}")
                except Exception as e:
                    logger.error(f"Failed to get node '{node_name}': {e}")
                    self.error_occurred.emit("Node Error", str(e))
                    return

                # Process this node
                self.progress_update.emit(
                    f"Processing {node_name} ({idx + 1}/{total_nodes})",
                    base_progress,
                    "Preparing to track..."
                )

                try:
                    start_time = time.time()
                    self._process_camera_tracker(
                        node,
                        node_name,
                        base_progress,
                        100.0 / total_nodes
                    )
                    elapsed = time.time() - start_time
                    logger.info(f"Completed {node_name} in {elapsed:.2f} seconds")
                except Exception as e:
                    logger.error(f"Error processing {node_name}: {e}", exc_info=True)
                    self.error_occurred.emit(
                        f"Error processing {node_name}",
                        f"Failed to process camera tracker:\n\n{str(e)}"
                    )
                    return

            # Complete
            logger.info("=" * 60)
            logger.info(f"AUTO TRACK COMPLETED SUCCESSFULLY - {total_nodes} node(s) processed")
            logger.info("=" * 60)
            self.tracking_complete.emit(
                True,
                f"Successfully processed {total_nodes} camera tracker(s)"
            )

        except Exception as e:
            logger.critical(f"Unexpected error in tracking process: {e}", exc_info=True)
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
        logger.info(f"\n--- Processing CameraTracker: {node_name} ---")

        # Show control panel
        logger.debug("Showing control panel...")
        nuke.executeInMainThread(node.showControlPanel)

        # Get current plate name
        try:
            plate_name = nuke.executeInMainThreadWithResult(
                lambda: nuke.tcl(f"full_name [topnode {node.name()}]")
            )
            logger.info(f"Plate name: {plate_name}")
        except Exception as e:
            logger.warning(f"Could not get plate name, using node name: {e}")
            plate_name = node_name

        # Track Features
        if self.cancelled:
            return

        logger.info("\n[STEP 1/4] TRACKING FEATURES")
        self.progress_update.emit(
            f"Tracking {node_name}",
            base_progress + (progress_range * 0.2),
            f"Tracking features on plate: {plate_name}"
        )

        # Execute tracking in main thread (CRITICAL FIX)
        logger.debug("Executing trackFeatures button...")
        start_time = time.time()
        nuke.executeInMainThread(lambda: node["trackFeatures"].execute())
        elapsed = time.time() - start_time

        # Check track count
        try:
            track_count = nuke.executeInMainThreadWithResult(
                lambda: len(node.knob('tracks').getValue())
            )
            logger.info(f"Tracking complete in {elapsed:.2f}s - {track_count} tracks created")
        except:
            logger.warning("Could not get track count")

        # Solve Camera
        if self.cancelled:
            return

        logger.info("\n[STEP 2/4] SOLVING CAMERA")
        self.progress_update.emit(
            f"Solving {node_name}",
            base_progress + (progress_range * 0.4),
            f"Solving camera for plate: {plate_name}"
        )

        logger.debug("Executing solveCamera button...")
        start_time = time.time()
        nuke.executeInMainThread(lambda: node["solveCamera"].execute())
        elapsed = time.time() - start_time

        # Check initial RMSE
        try:
            initial_rmse = nuke.executeInMainThreadWithResult(
                lambda: node['solveRMSE'].value()
            )
            logger.info(f"Camera solved in {elapsed:.2f}s - Initial RMSE: {initial_rmse:.4f}")
        except:
            logger.warning("Could not get initial RMSE")

        # Recursive update solve
        if self.cancelled:
            return

        logger.info("\n[STEP 3/4] RECURSIVE SOLVE REFINEMENT")
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

        logger.info("\n[STEP 4/4] CREATING CAMERA NODE")
        self.progress_update.emit(
            f"Creating camera for {node_name}",
            base_progress + (progress_range * 0.9),
            f"Generating camera node: {self.params['camera_prefix']}{plate_name}"
        )

        # Store current cameras to find the new one
        cameras_before = nuke.executeInMainThreadWithResult(
            lambda: set(nuke.allNodes('Camera3'))
        )
        logger.debug(f"Cameras before: {len(cameras_before)}")

        # Create camera using the enhanced function (in main thread)
        logger.debug("Creating camera node...")
        start_time = time.time()
        camera_node = nuke.executeInMainThreadWithResult(
            lambda: self._create_camera(node)
        )
        elapsed = time.time() - start_time
        logger.info(f"Camera created in {elapsed:.2f}s")

        # Find and rename the new camera
        cameras_after = nuke.executeInMainThreadWithResult(
            lambda: set(nuke.allNodes('Camera3'))
        )
        new_cameras = cameras_after - cameras_before
        logger.debug(f"Cameras after: {len(cameras_after)}, New cameras: {len(new_cameras)}")

        if new_cameras:
            camera_node = list(new_cameras)[0]
            final_name = f"{self.params['camera_prefix']}{plate_name}"
            nuke.executeInMainThread(lambda: camera_node.setName(final_name))
            logger.info(f"Camera renamed to: {final_name}")

            self.progress_update.emit(
                f"Completed {node_name}",
                base_progress + progress_range,
                f"Created camera: {final_name}"
            )
        else:
            logger.warning("No new camera found after creation!")

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
        logger.debug("Updating solve...")

        # Get reference frames (in main thread)
        refFrames = nuke.executeInMainThreadWithResult(
            lambda: [cameraTracker['trackStart'].value(), cameraTracker['trackStop'].value()]
        )
        logger.debug(f"Reference frames: {refFrames}")

        # Update selected frames knob (in main thread)
        def update_frames():
            selFrameKnob = cameraTracker.knob('selectedFrames')
            selFrameKnob.clearAnimated()
            selFrameKnob.setAnimated()
            for frame in refFrames:
                selFrameKnob.setValueAt(frame, frame)

        nuke.executeInMainThread(update_frames)

        # Execute update solve button (in main thread)
        nuke.executeInMainThread(lambda: cameraTracker.knob("doUpdateSolve").execute())
        logger.debug("Solve updated")

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

        logger.info(f"Starting recursive refinement - Target RMSE: {controlError}, Max iterations: {max_iter}")

        iteration = 0

        current_rmse = nuke.executeInMainThreadWithResult(lambda: node['solveRMSE'].value())

        while current_rmse >= controlError and iteration < max_iter:
            if self.cancelled:
                logger.info("Recursive refinement cancelled by user")
                return

            logger.debug(f"Iteration {iteration + 1}/{max_iter} - Current RMSE: {current_rmse:.4f}")

            # Update thresholds (in main thread)
            nuke.executeInMainThread(lambda: node['minLengthThreshold'].setValue(minLen))
            nuke.executeInMainThread(lambda: node['maxRMSEThreshold'].setValue(maxTrackError))
            nuke.executeInMainThread(lambda: node['maxErrorThreshold'].setValue(maxError))
            logger.debug(f"Set thresholds - minLen: {minLen}, maxTrackError: {maxTrackError:.2f}, maxError: {maxError:.2f}")

            # Delete rejected tracks
            nuke.executeInMainThread(lambda: node['deleteRejectedTracks'].setValue(
                "cameraTracker = nuke.thisNode()\n"
                "cameraTracker['proceedWithUpdate'].setValue(True)"
            ))
            nuke.executeInMainThread(lambda: node['deleteRejectedTracks'].execute())
            logger.debug("Deleted rejected tracks")

            # Delete invalid tracks
            nuke.executeInMainThread(lambda: node['deleteInvalidTracks'].setValue(
                "cameraTracker = nuke.thisNode()\n"
                "cameraTracker['proceedWithUpdate'].setValue(True)"
            ))
            nuke.executeInMainThread(lambda: node['deleteInvalidTracks'].execute())
            logger.debug("Deleted invalid tracks")

            # Update solve
            self._update_solve(node)

            new_rmse = nuke.executeInMainThreadWithResult(lambda: node['solveRMSE'].value())
            improvement = current_rmse - new_rmse

            logger.info(f"Iteration {iteration + 1} complete - RMSE: {current_rmse:.4f} → {new_rmse:.4f} (Δ {improvement:.4f})")

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
            current_rmse = new_rmse

        # Final status
        final_rmse = nuke.executeInMainThreadWithResult(lambda: node['solveRMSE'].value())
        final_detail = (
            f"Refinement complete after {iteration} iteration(s) | "
            f"Final RMSE: {final_rmse:.4f}"
        )

        if final_rmse < controlError:
            logger.info(f"✓ Target RMSE achieved: {final_rmse:.4f} < {controlError:.4f}")
        else:
            logger.warning(f"Target RMSE not achieved: {final_rmse:.4f} >= {controlError:.4f} (max iterations reached)")

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
