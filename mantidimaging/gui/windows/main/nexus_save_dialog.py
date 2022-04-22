# Copyright (C) 2022 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later
import uuid
from typing import Optional, List

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFileDialog

from mantidimaging.core.data.dataset import StrictDataset
from mantidimaging.gui.utility import compile_ui


class NexusSaveDialog(QDialog):

    selected_dataset = Optional[uuid.UUID]

    def __init__(self, parent, dataset_list: List[StrictDataset]):
        super().__init__(parent)
        compile_ui('gui/ui/nexus_save_dialog.ui', self)

        self.browseButton.clicked.connect(self._set_save_path)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).clicked.connect(self.save)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        self.savePath.textChanged.connect(self.enable_save)
        self.sampleNameLineEdit.textChanged.connect(self.enable_save)

        self.dataset_uuids: List[uuid.UUID] = []
        self._create_dataset_lists(dataset_list)

        self.selected_dataset = None

    def _create_dataset_lists(self, dataset_list):
        if dataset_list:
            self.dataset_uuids, dataset_names = zip(*dataset_list)
            self.datasetNames.addItems(dataset_names)

    def save(self):
        self.selected_dataset = self.dataset_uuids[self.datasetNames.currentIndex()]
        self.parent().execute_nexus_save()

    def save_path(self) -> str:
        """
        :return: The directory of the path as a Python string
        """
        return str(self.savePath.text())

    def sample_name(self) -> str:
        return str(self.sampleNameLineEdit.text())

    def enable_save(self):
        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(self.save_path() != ""
                                                                               and self.sample_name() != "")

    def _set_save_path(self):
        path = QFileDialog.getSaveFileName(self, "Save NeXus file", "", "NeXus (*.nxs)")[0]
        self.savePath.setText(path)