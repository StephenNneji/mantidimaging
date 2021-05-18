# Copyright (C) 2020 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later

from logging import getLogger
from mantidimaging.core.utility.projection_angle_parser import ProjectionAngleFileParser
from typing import Optional
from uuid import UUID

from PyQt5 import Qt, QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QDialog, QInputDialog, QLabel, QMessageBox

from mantidimaging.gui.widgets.stack_selector_dialog.stack_selector_dialog import StackSelectorDialog

from mantidimaging.core.data import Images
from mantidimaging.core.utility.version_check import check_version_and_label
from mantidimaging.gui.dialogs.multiple_stack_select.view import MultipleStackSelect
from mantidimaging.gui.mvp_base import BaseMainWindowView
from mantidimaging.gui.windows.load_dialog import MWLoadDialog
from mantidimaging.gui.windows.main.presenter import MainWindowPresenter
from mantidimaging.gui.windows.main.presenter import Notification as PresNotification
from mantidimaging.gui.windows.main.save_dialog import MWSaveDialog
from mantidimaging.gui.windows.operations import FiltersWindowView
from mantidimaging.gui.windows.recon import ReconstructWindowView
from mantidimaging.gui.windows.savu_operations.view import SavuFiltersWindowView
from mantidimaging.gui.windows.stack_choice.compare_presenter import StackComparePresenter
from mantidimaging.gui.windows.stack_visualiser import StackVisualiserView

LOG = getLogger(__file__)


class MainWindowView(BaseMainWindowView):
    AVAILABLE_MSG = "Savu Backend not available"
    NOT_THE_LATEST_VERSION = "This is not the latest version"
    UNCAUGHT_EXCEPTION = "Uncaught exception"

    active_stacks_changed = Qt.pyqtSignal()
    backend_message = Qt.pyqtSignal(bytes)

    actionRecon: QAction
    actionFilters: QAction
    actionSavuFilters: QAction
    actionCompareImages: QAction
    actionLoadLog: QAction
    actionLoadProjectionAngles: QAction
    actionLoad180deg: QAction
    actionLoad: QAction
    actionSave: QAction
    actionExit: QAction

    filters: Optional[FiltersWindowView] = None
    savu_filters: Optional[SavuFiltersWindowView] = None
    recon: Optional[ReconstructWindowView] = None

    load_dialogue: Optional[MWLoadDialog] = None
    save_dialogue: Optional[MWSaveDialog] = None

    actionDebug_Me: QAction

    def __init__(self):
        super(MainWindowView, self).__init__(None, "gui/ui/main_window.ui")

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Mantid Imaging")

        self.presenter = MainWindowPresenter(self)

        status_bar = self.statusBar()
        self.status_bar_label = QLabel("", self)
        status_bar.addPermanentWidget(self.status_bar_label)

        self.setup_shortcuts()
        self.update_shortcuts()
        is_main_label = check_version_and_label(self.not_latest_version_warning)

        if not is_main_label:
            self.setWindowTitle("Mantid Imaging Unstable")
            self.setWindowIcon(QIcon("./images/mantid_imaging_unstable_64px.png"))

    def setup_shortcuts(self):
        self.actionLoad.triggered.connect(self.show_load_dialogue)
        self.actionSampleLoadLog.triggered.connect(self.load_sample_log_dialog)
        self.actionLoad180deg.triggered.connect(self.load_180_deg_dialog)
        self.actionLoadProjectionAngles.triggered.connect(self.load_projection_angles)
        self.actionSave.triggered.connect(self.show_save_dialogue)
        self.actionExit.triggered.connect(self.close)

        self.actionOnlineDocumentation.triggered.connect(self.open_online_documentation)
        self.actionAbout.triggered.connect(self.show_about)

        self.actionFilters.triggered.connect(self.show_savu_filters_window)
        self.actionRecon.triggered.connect(self.show_recon_window)

        self.actionCompareImages.triggered.connect(self.show_stack_select_dialog)

        self.active_stacks_changed.connect(self.update_shortcuts)

        self.actionDebug_Me.triggered.connect(self.attach_debugger)

    def update_shortcuts(self):
        self.actionSave.setEnabled(len(self.presenter.stack_names) > 0)

    @staticmethod
    def open_online_documentation():
        url = QtCore.QUrl("https://mantidproject.github.io/mantidimaging/")
        QtGui.QDesktopServices.openUrl(url)

    def show_about(self):
        from mantidimaging import __version__ as version_no

        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("About MantidImaging")
        msg_box.setTextFormat(QtCore.Qt.RichText)
        msg_box.setText(
            '<a href="https://github.com/mantidproject/mantidimaging">MantidImaging</a>'
            '<br>Version: <a href="https://github.com/mantidproject/mantidimaging/releases/tag/{0}">{0}</a>'.format(
                version_no))
        msg_box.show()

    def show_load_dialogue(self):
        self.load_dialogue = MWLoadDialog(self)
        self.load_dialogue.show()

    def load_sample_log_dialog(self):
        stack_selector = StackSelectorDialog(main_window=self,
                                             title="Stack Selector",
                                             message="Which stack is the log being loaded for?")
        # Was closed without accepting (e.g. via x button or ESC)
        if QDialog.Accepted != stack_selector.exec():
            return
        stack_to_add_log_to = stack_selector.selected_stack

        # Open file dialog
        file_filter = "Log File (*.txt *.log)"
        selected_file, _ = Qt.QFileDialog.getOpenFileName(caption="Log to be loaded",
                                                          filter=f"{file_filter};;All (*.*)",
                                                          initialFilter=file_filter)
        # Cancel/Close was clicked
        if selected_file == "":
            return

        self.presenter.add_log_to_sample(stack_name=stack_to_add_log_to, log_file=selected_file)

        QMessageBox.information(self, "Load complete", f"{selected_file} was loaded as a log into "
                                f"{stack_to_add_log_to}.")

    def load_180_deg_dialog(self):
        stack_selector = StackSelectorDialog(main_window=self,
                                             title="Stack Selector",
                                             message="Which stack is the 180 degree projection being loaded for?")
        # Was closed without accepting (e.g. via x button or ESC)
        if QDialog.Accepted != stack_selector.exec():
            return
        stack_to_add_180_deg_to = stack_selector.selected_stack

        # Open file dialog
        file_filter = "Image File (*.tif *.tiff)"
        selected_file, _ = Qt.QFileDialog.getOpenFileName(caption="180 Degree Image",
                                                          filter=f"{file_filter};;All (*.*)",
                                                          initialFilter=file_filter)
        # Cancel/Close was clicked
        if selected_file == "":
            return

        _180_dataset = self.presenter.add_180_deg_to_sample(stack_name=stack_to_add_180_deg_to,
                                                            _180_deg_file=selected_file)
        self.create_new_stack(_180_dataset, self.presenter.create_stack_name(selected_file))

    LOAD_PROJECTION_ANGLES_DIALOG_MESSAGE = "Which stack are the projection angles in DEGREES being loaded for?"
    LOAD_PROJECTION_ANGLES_FILE_DIALOG_CAPTION = "File with projection angles in DEGREES"

    def load_projection_angles(self):
        stack_selector = StackSelectorDialog(main_window=self,
                                             title="Stack Selector",
                                             message=self.LOAD_PROJECTION_ANGLES_DIALOG_MESSAGE)
        # Was closed without accepting (e.g. via x button or ESC)
        if QDialog.Accepted != stack_selector.exec():
            return

        stack_name = stack_selector.selected_stack

        selected_file, _ = Qt.QFileDialog.getOpenFileName(caption=self.LOAD_PROJECTION_ANGLES_FILE_DIALOG_CAPTION,
                                                          filter="All (*.*)")
        if selected_file == "":
            return

        pafp = ProjectionAngleFileParser(selected_file)
        projection_angles = pafp.get_projection_angles()

        self.presenter.add_projection_angles_to_sample(stack_name, projection_angles)
        QMessageBox.information(self, "Load complete", f"Angles from {selected_file} were loaded into into "
                                f"{stack_name}.")

    def execute_save(self):
        self.presenter.notify(PresNotification.SAVE)

    def execute_load(self):
        self.presenter.notify(PresNotification.LOAD)

    def show_save_dialogue(self):
        self.save_dialogue = MWSaveDialog(self, self.stack_list)
        self.save_dialogue.show()

    def show_recon_window(self):
        if not self.recon:
            self.recon = ReconstructWindowView(self)
            self.recon.show()
        else:
            self.recon.activateWindow()
            self.recon.raise_()

    def show_filters_window(self):
        if not self.filters:
            self.filters = FiltersWindowView(self)
            self.filters.show()
        else:
            self.filters.activateWindow()
            self.filters.raise_()

    def show_savu_filters_window(self):
        if not self.savu_filters:
            try:
                self.savu_filters = SavuFiltersWindowView(self)
                self.savu_filters.show()
            except RuntimeError as e:
                QtWidgets.QMessageBox.warning(self, self.AVAILABLE_MSG, str(e))
        else:
            self.savu_filters.activateWindow()
            self.savu_filters.raise_()

    @property
    def stack_list(self):
        return self.presenter.stack_list

    @property
    def stack_names(self):
        return self.presenter.stack_names

    def get_stack_visualiser(self, stack_uuid):
        return self.presenter.get_stack_visualiser(stack_uuid)

    def get_all_stack_visualisers(self):
        return self.presenter.get_all_stack_visualisers()

    def get_all_stack_visualisers_with_180deg_proj(self):
        return self.presenter.get_all_stack_visualisers_with_180deg_proj()

    def get_stack_history(self, stack_uuid):
        return self.presenter.get_stack_history(stack_uuid)

    def create_new_stack(self, images: Images, title: str):
        self.presenter.create_new_stack(images, title)

    def update_stack_with_images(self, images: Images):
        self.presenter.update_stack_with_images(images)

    def get_stack_with_images(self, images: Images) -> StackVisualiserView:
        return self.presenter.get_stack_with_images(images)

    def create_stack_window(self,
                            stack: Images,
                            title: str,
                            position=QtCore.Qt.TopDockWidgetArea,
                            floating=False) -> Qt.QDockWidget:
        dock = Qt.QDockWidget(title, self)

        # this puts the new stack window into the centre of the window
        self.setCentralWidget(dock)

        # add the dock widget into the main window
        self.addDockWidget(position, dock)

        # we can get the stack visualiser widget with dock_widget.widget
        dock.setWidget(StackVisualiserView(self, dock, stack))

        dock.setFloating(floating)

        return dock

    def remove_stack(self, obj: StackVisualiserView):
        getLogger(__name__).debug("Removing stack with uuid %s", obj.uuid)
        self.presenter.notify(PresNotification.REMOVE_STACK, uuid=obj.uuid)

    def rename_stack(self, current_name: str, new_name: str):
        self.presenter.notify(PresNotification.RENAME_STACK, current_name=current_name, new_name=new_name)

    def closeEvent(self, event):
        """
        Handles a request to quit the application from the user.
        """
        should_close = True

        if self.presenter.have_active_stacks:
            # Show confirmation box asking if the user really wants to quit if
            # they have data loaded
            msg_box = QtWidgets.QMessageBox.question(self,
                                                     "Quit",
                                                     "Are you sure you want to quit with loaded data?",
                                                     defaultButton=QtWidgets.QMessageBox.No)
            should_close = msg_box == QtWidgets.QMessageBox.Yes

        if should_close:
            # allows to properly cleanup the socket IO connection
            if self.savu_filters:
                self.savu_filters.close()

            # Pass close event to parent
            super(MainWindowView, self).closeEvent(event)

        else:
            # Ignore the close event, keeping window open
            event.ignore()

    def not_latest_version_warning(self, msg: str):
        QtWidgets.QMessageBox.warning(self, self.NOT_THE_LATEST_VERSION, msg)

    def uncaught_exception(self, user_error_msg, log_error_msg):
        QtWidgets.QMessageBox.critical(self, self.UNCAUGHT_EXCEPTION, f"{user_error_msg}")
        getLogger(__name__).error(log_error_msg)

    def attach_debugger(self):
        port, accepted = QInputDialog.getInt(self, "Debug port", "Get PyCharm debug listen port", value=25252)
        if accepted:
            import pydevd_pycharm
            pydevd_pycharm.settrace('ndlt1104.isis.cclrc.ac.uk', port=port, stdoutToServer=True, stderrToServer=True)

    def show_stack_select_dialog(self):
        dialog = MultipleStackSelect(self)
        if dialog.exec() == QDialog.Accepted:
            one = self.presenter.get_stack_visualiser(dialog.stack_one.current()).presenter.images
            two = self.presenter.get_stack_visualiser(dialog.stack_two.current()).presenter.images

            stack_choice = StackComparePresenter(one, two, self)
            stack_choice.show()

    def set_images_in_stack(self, uuid: UUID, images: Images):
        self.presenter.set_images_in_stack(uuid, images)

    def find_images_stack_title(self, images: Images) -> str:
        return self.presenter.get_stack_with_images(images).name
