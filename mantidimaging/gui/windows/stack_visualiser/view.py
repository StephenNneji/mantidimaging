# Copyright (C) 2021 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later

from typing import TYPE_CHECKING

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QAction, QDockWidget, QInputDialog, QMenu, QMessageBox, QVBoxLayout, QWidget

from mantidimaging.core.data import Images
from mantidimaging.core.utility.sensible_roi import SensibleROI
from mantidimaging.gui.dialogs.op_history_copy.view import OpHistoryCopyDialogView
from mantidimaging.gui.widgets.mi_image_view.view import MIImageView

from ...mvp_base import BaseMainWindowView
from ...utility.common import operation_in_progress
from ..stack_visualiser.presenter import StackVisualiserPresenter
from .metadata_dialog import MetadataDialog
from .presenter import SVNotification
from ...utility.qt_helpers import populate_menu

if TYPE_CHECKING:
    from mantidimaging.gui.windows.main import MainWindowView  # noqa:F401   # pragma: no cover


class StackVisualiserView(BaseMainWindowView):
    # Signal that signifies when the ROI is updated. Used to update previews in Filter views
    roi_updated = pyqtSignal(SensibleROI)

    image_view: MIImageView
    presenter: StackVisualiserPresenter
    dock: QDockWidget
    layout: QVBoxLayout

    def __init__(self, parent: 'MainWindowView', dock: QDockWidget, images: Images):
        # enforce not showing a single image
        assert images.data.ndim == 3, \
            "Data does NOT have 3 dimensions! Dimensions found: {0}".format(images.data.ndim)

        # We set the main window as the parent, the effect is the same as
        # having no parent, the window will be inside the QDockWidget. If the
        # dock is set as a parent the window will be an independent floating
        # window
        super(StackVisualiserView, self).__init__(parent, None)
        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self)
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)
        self.parent_create_stack = self.parent().create_new_stack
        self._main_window = parent

        # capture the QDockWidget reference so that we can access the Qt widget
        # and change things like the title
        self.dock = dock
        # Swap out the dock close event with our own provided close event. This
        # is needed to manually delete the data reference, otherwise it is left
        # hanging in the presenter
        setattr(dock, 'closeEvent', self.closeEvent)

        self.presenter = StackVisualiserPresenter(self, images)

        self._actions = [
            ("Show history and metadata", self.show_image_metadata),
            ("Duplicate whole data", lambda: self.presenter.notify(SVNotification.DUPE_STACK)),
            ("Duplicate current ROI of data", lambda: self.presenter.notify(SVNotification.DUPE_STACK_ROI)),
            ("Mark as projections/sinograms", self.mark_as_sinograms), ("", None),
            ("Toggle show averaged image", lambda: self.presenter.notify(SVNotification.TOGGLE_IMAGE_MODE)),
            ("Create sinograms from stack", lambda: self.presenter.notify(SVNotification.SWAP_AXES)),
            ("Set ROI", self.set_roi), ("Copy ROI to clipboard", self.copy_roi_to_clipboard), ("", None),
            ("Change window name", self.change_window_name_clicked), ("Goto projection", self.goto_projection),
            ("Goto angle", self.goto_angle)
        ]
        self._context_actions = self.build_context_menu()

        self.image_view = MIImageView(self)
        self.image_view.imageItem.menu = self._context_actions
        self.actionCloseStack = QAction("Close window", self)
        self.actionCloseStack.triggered.connect(self.close)
        self.actionCloseStack.setShortcut("Ctrl+W")
        self.dock.addAction(self.actionCloseStack)
        self.image_view.setImage(self.presenter.images.data)
        self.image_view.roi_changed_callback = self.roi_changed_callback
        self.layout.addWidget(self.image_view)

    @property
    def name(self):
        return self.dock.windowTitle()

    @name.setter
    def name(self, name: str):
        self.dock.setWindowTitle(name)

    @property
    def current_roi(self) -> SensibleROI:
        return SensibleROI.from_points(*self.image_view.get_roi())

    @property
    def image(self):
        return self.image_view.imageItem

    @image.setter
    def image(self, to_display):
        self.image_view.setImage(to_display)

    @property
    def main_window(self) -> 'MainWindowView':
        return self._main_window

    @property
    def context_actions(self):
        return self._context_actions

    @property
    def actions(self):
        return self._actions

    def closeEvent(self, event):
        window: 'MainWindowView' = self.window()
        stacks_with_proj180 = window.get_all_stack_visualisers_with_180deg_proj()
        for stack in stacks_with_proj180:
            if stack.presenter.images.proj180deg is self.presenter.images:
                if not self.ask_confirmation(
                        "Caution: If you close this then the 180 degree projection will "
                        "not be available for COR correlation, and the middle of the image stack will be used."):
                    event.ignore()
                    return
                else:
                    stack.presenter.images.clear_proj180deg()

        with operation_in_progress("Closing image view", "Freeing image memory"):
            self.dock.setFloating(False)
            self.hide()
            self.image_view.close()

            # this removes a hanging reference from the presenter to the data
            # allowing it to be GC'ed
            self.presenter.delete_data()
            window.remove_stack(self)
            self.deleteLater()
            # refers to the QDockWidget within which the stack is contained
            self.dock.deleteLater()

    def roi_changed_callback(self, roi: SensibleROI):
        self.roi_updated.emit(roi)

    def build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        populate_menu(menu, self.actions)
        return menu

    def goto_projection(self):
        projection_to_goto, accepted = QInputDialog.getInt(
            self,
            "Enter Projection",
            "Projection",
            0,  # Default value
            0,  # Min projection value
            self.presenter.get_num_images(),  # Max possible value
        )
        if accepted:
            self.image_view.set_selected_image(projection_to_goto)

    def goto_angle(self):
        projection_to_goto, accepted = QInputDialog.getDouble(
            self,
            "Enter Angle",
            "Angle in Degrees",
            0,  # Default value
            0,  # Min projection value
            2147483647,  # Max possible value
            4,  # Digits/decimals
        )
        if accepted:
            self.image_view.set_selected_image(self.presenter.find_image_from_angle(projection_to_goto))

    def set_roi(self):
        roi, accepted = QInputDialog.getText(
            self,
            "Manual ROI",
            "Enter ROI in order left, top, right, bottom, with commas in-between each number",
            text="0, 0, 50, 50")
        if accepted:
            roi = [int(r.strip()) for r in roi.split(",")]
            self.image_view.roi.setPos((roi[0], roi[1]), update=False)
            self.image_view.roi.setSize((roi[2] - roi[0], roi[3] - roi[1]))
            self.image_view.roi.show()
            self.image_view.roiChanged()

    def copy_roi_to_clipboard(self):
        pos, size = self.image_view.get_roi()
        QGuiApplication.clipboard().setText(f"{pos.x}, {pos.y}, {pos.x + size.x}, {pos.y + size.y}")

    def change_window_name_clicked(self):
        input_window = QInputDialog()
        new_window_name, ok = input_window.getText(self, "Change window name", "Name:", text=self.name)
        if ok:
            if new_window_name not in self.main_window.stack_names:
                self.main_window.rename_stack(self.name, new_window_name)
            else:
                error = QMessageBox(self)
                error.setWindowTitle("Stack name conflict")
                error.setText(f"There is already a window named {new_window_name}")
                error.exec()

    def show_image_metadata(self):
        dialog = MetadataDialog(self, self.presenter.images)
        dialog.show()

    def show_op_history_copy_dialog(self):
        dialog = OpHistoryCopyDialogView(self, self.presenter.images, self.main_window)
        dialog.show()

    def mark_as_sinograms(self):
        # 1 is position of sinograms, 0 is projections
        current = 1 if self.presenter.images._is_sinograms else 0
        item, accepted = QInputDialog.getItem(self, "Select if projections or sinograms", "Images are:",
                                              ["projections", "sinograms"], current)
        if accepted:
            self.presenter.images._is_sinograms = False if item == "projections" else True

    def ask_confirmation(self, msg: str):
        response = QMessageBox.question(self, "Confirm action", msg, QMessageBox.Ok | QMessageBox.Cancel)  # type:ignore
        return response == QMessageBox.Ok
