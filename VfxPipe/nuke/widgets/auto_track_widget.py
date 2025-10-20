"""
Auto Track Widget - Qt Interface for Camera Tracking Automation

Provides a Qt-based interface for automated camera tracking in Nuke.
Allows users to select CameraTracker nodes and configure tracking parameters.
"""

from VfxPipe.utils.host import getPySideVersion

# Dynamically import correct PySide version based on DCC
_pyside_version = getPySideVersion()

try:
    if _pyside_version == 2:
        from PySide2 import QtWidgets, QtCore, QtGui
    else:
        from PySide6 import QtWidgets, QtCore, QtGui
except ImportError as e:
    raise ImportError(
        f"PySide{_pyside_version} is required for this DCC but not available. "
        f"Please install PySide{_pyside_version}. Error: {e}"
    )


class AutoTrackWidget(QtWidgets.QDialog):
    """
    Qt widget for configuring and executing automated camera tracking.

    Features:
    - Node selection table with checkboxes
    - Configurable tracking parameters
    - Progress tracking with detailed status
    - Camera naming options
    """

    # Signals for communication between UI and worker thread
    start_tracking = QtCore.Signal(dict)
    cancel_tracking = QtCore.Signal()

    def __init__(self, parent=None):
        super(AutoTrackWidget, self).__init__(parent)

        self.setWindowTitle("Auto Track - Camera Tracking Automation")
        self.setMinimumSize(700, 600)
        self.resize(800, 700)

        # Track processing state
        self.is_processing = False

        # Build UI
        self._build_ui()

        # Populate with selected nodes
        self.refresh_nodes()

    def _build_ui(self):
        """Construct the user interface."""
        main_layout = QtWidgets.QVBoxLayout(self)

        # Title
        title = QtWidgets.QLabel("Camera Tracker Automation")
        title_font = QtGui.QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # Separator
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        main_layout.addWidget(line)

        # Node Selection Section
        node_group = QtWidgets.QGroupBox("CameraTracker Nodes (Selected)")
        node_layout = QtWidgets.QVBoxLayout()

        # Refresh button
        refresh_btn = QtWidgets.QPushButton("Refresh from Selection")
        refresh_btn.clicked.connect(self.refresh_nodes)
        node_layout.addWidget(refresh_btn)

        # Node table
        self.node_table = QtWidgets.QTableWidget()
        self.node_table.setColumnCount(3)
        self.node_table.setHorizontalHeaderLabels(["Process", "Node Name", "Input Plate"])
        self.node_table.horizontalHeader().setStretchLastSection(True)
        self.node_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.node_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.node_table.setColumnWidth(0, 60)
        self.node_table.setColumnWidth(1, 250)
        node_layout.addWidget(self.node_table)

        # Select/Deselect all buttons
        button_layout = QtWidgets.QHBoxLayout()
        select_all_btn = QtWidgets.QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_nodes)
        deselect_all_btn = QtWidgets.QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all_nodes)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addStretch()
        node_layout.addLayout(button_layout)

        node_group.setLayout(node_layout)
        main_layout.addWidget(node_group)

        # Parameters Section
        params_group = QtWidgets.QGroupBox("Tracking Parameters")
        params_layout = QtWidgets.QFormLayout()

        # Recursive tracking parameters
        self.min_len_spin = QtWidgets.QSpinBox()
        self.min_len_spin.setRange(1, 100)
        self.min_len_spin.setValue(3)
        self.min_len_spin.setToolTip("Minimum track length threshold")
        params_layout.addRow("Min Track Length:", self.min_len_spin)

        self.max_track_error_spin = QtWidgets.QDoubleSpinBox()
        self.max_track_error_spin.setRange(0.1, 20.0)
        self.max_track_error_spin.setValue(4.0)
        self.max_track_error_spin.setSingleStep(0.25)
        self.max_track_error_spin.setToolTip("Maximum RMSE threshold for tracks")
        params_layout.addRow("Max Track Error:", self.max_track_error_spin)

        self.max_error_spin = QtWidgets.QDoubleSpinBox()
        self.max_error_spin.setRange(0.1, 20.0)
        self.max_error_spin.setValue(4.0)
        self.max_error_spin.setSingleStep(0.25)
        self.max_error_spin.setToolTip("Maximum error threshold")
        params_layout.addRow("Max Error:", self.max_error_spin)

        self.control_error_spin = QtWidgets.QDoubleSpinBox()
        self.control_error_spin.setRange(0.1, 10.0)
        self.control_error_spin.setValue(1.0)
        self.control_error_spin.setSingleStep(0.1)
        self.control_error_spin.setToolTip("Target RMSE to achieve")
        params_layout.addRow("Control Error:", self.control_error_spin)

        self.max_iter_spin = QtWidgets.QSpinBox()
        self.max_iter_spin.setRange(1, 20)
        self.max_iter_spin.setValue(5)
        self.max_iter_spin.setToolTip("Maximum number of recursive iterations")
        params_layout.addRow("Max Iterations:", self.max_iter_spin)

        # Camera naming
        self.camera_prefix_edit = QtWidgets.QLineEdit("cam_")
        self.camera_prefix_edit.setToolTip("Prefix for generated camera names")
        params_layout.addRow("Camera Name Prefix:", self.camera_prefix_edit)

        # Link camera output
        self.link_output_check = QtWidgets.QCheckBox("Link camera to solver (expressions)")
        self.link_output_check.setChecked(False)
        self.link_output_check.setToolTip("If checked, uses expressions. If unchecked, bakes values.")
        params_layout.addRow("Link Output:", self.link_output_check)

        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)

        # Progress Section
        progress_group = QtWidgets.QGroupBox("Progress")
        progress_layout = QtWidgets.QVBoxLayout()

        self.status_label = QtWidgets.QLabel("Ready to track...")
        self.status_label.setWordWrap(True)
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.detail_label = QtWidgets.QLabel("")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("color: #666; font-size: 10px;")
        progress_layout.addWidget(self.detail_label)

        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        # Action Buttons
        button_box = QtWidgets.QHBoxLayout()

        self.track_btn = QtWidgets.QPushButton("Track Cameras")
        self.track_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; }")
        self.track_btn.clicked.connect(self._on_track_clicked)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.close)

        button_box.addWidget(self.track_btn)
        button_box.addWidget(self.cancel_btn)
        button_box.addStretch()
        button_box.addWidget(close_btn)

        main_layout.addLayout(button_box)

    def refresh_nodes(self):
        """Refresh the node table with currently selected CameraTracker nodes."""
        try:
            import nuke

            # Get selected CameraTracker nodes
            # BUG: No type validation! This will allow any node type to be processed
            selected_nodes = [n for n in nuke.selectedNodes()]

            # Clear table
            self.node_table.setRowCount(0)

            if not selected_nodes:
                self.status_label.setText("No CameraTracker nodes selected. Please select nodes and click Refresh.")
                return

            # Populate table
            for node in selected_nodes:
                row = self.node_table.rowCount()
                self.node_table.insertRow(row)

                # Checkbox
                check_widget = QtWidgets.QWidget()
                check_layout = QtWidgets.QHBoxLayout(check_widget)
                check_layout.setAlignment(QtCore.Qt.AlignCenter)
                check_layout.setContentsMargins(0, 0, 0, 0)
                checkbox = QtWidgets.QCheckBox()
                checkbox.setChecked(True)
                check_layout.addWidget(checkbox)
                self.node_table.setCellWidget(row, 0, check_widget)

                # Node name
                name_item = QtWidgets.QTableWidgetItem(node.name())
                self.node_table.setItem(row, 1, name_item)

                # Input plate name
                try:
                    plate_name = nuke.tcl(f"full_name [topnode {node.name()}]")
                except:
                    plate_name = "Unknown"
                plate_item = QtWidgets.QTableWidgetItem(plate_name)
                self.node_table.setItem(row, 2, plate_item)

            self.status_label.setText(f"Loaded {len(selected_nodes)} CameraTracker node(s)")

        except ImportError:
            self.status_label.setText("Error: Nuke not available")
        except Exception as e:
            self.status_label.setText(f"Error refreshing nodes: {str(e)}")

    def _select_all_nodes(self):
        """Check all node checkboxes."""
        for row in range(self.node_table.rowCount()):
            check_widget = self.node_table.cellWidget(row, 0)
            checkbox = check_widget.findChild(QtWidgets.QCheckBox)
            if checkbox:
                checkbox.setChecked(True)

    def _deselect_all_nodes(self):
        """Uncheck all node checkboxes."""
        for row in range(self.node_table.rowCount()):
            check_widget = self.node_table.cellWidget(row, 0)
            checkbox = check_widget.findChild(QtWidgets.QCheckBox)
            if checkbox:
                checkbox.setChecked(False)

    def get_selected_nodes(self):
        """
        Get list of checked node names.

        Returns:
            List of node names that are checked
        """
        selected = []
        for row in range(self.node_table.rowCount()):
            check_widget = self.node_table.cellWidget(row, 0)
            checkbox = check_widget.findChild(QtWidgets.QCheckBox)
            if checkbox and checkbox.isChecked():
                node_name = self.node_table.item(row, 1).text()
                selected.append(node_name)
        return selected

    def get_parameters(self):
        """
        Get all tracking parameters from the UI.

        Returns:
            Dictionary of parameter values
        """
        return {
            'minLen': self.min_len_spin.value(),
            'maxTrackError': self.max_track_error_spin.value(),
            'maxError': self.max_error_spin.value(),
            'controlError': self.control_error_spin.value(),
            'max_iter': self.max_iter_spin.value(),
            'camera_prefix': self.camera_prefix_edit.text(),
            'link_output': self.link_output_check.isChecked()
        }

    def _on_track_clicked(self):
        """Handle Track button click."""
        # Get selected nodes
        selected_nodes = self.get_selected_nodes()

        if not selected_nodes:
            QtWidgets.QMessageBox.warning(
                self,
                "No Nodes Selected",
                "Please select at least one CameraTracker node to process."
            )
            return

        # Get parameters
        params = self.get_parameters()
        params['nodes'] = selected_nodes

        # Update UI state
        self.is_processing = True
        self.track_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)

        # Emit signal to start tracking
        self.start_tracking.emit(params)

    def _on_cancel_clicked(self):
        """Handle Cancel button click."""
        self.cancel_tracking.emit()
        self.update_status("Cancelling...", 0)

    def update_status(self, message, progress, detail=""):
        """
        Update the progress display.

        Args:
            message: Main status message
            progress: Progress percentage (0-100)
            detail: Detailed information
        """
        self.status_label.setText(message)
        self.progress_bar.setValue(int(progress))
        self.detail_label.setText(detail)

    def tracking_complete(self, success=True, message=""):
        """
        Call when tracking is complete.

        Args:
            success: Whether tracking completed successfully
            message: Completion message
        """
        self.is_processing = False
        self.track_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(100 if success else 0)

        if success:
            self.status_label.setText(message or "Tracking complete!")
            self.detail_label.setText("")
        else:
            self.status_label.setText("Tracking failed or cancelled")

    def show_error(self, title, message):
        """
        Display error dialog.

        Args:
            title: Error dialog title
            message: Error message
        """
        QtWidgets.QMessageBox.critical(self, title, message)
        self.tracking_complete(success=False)
