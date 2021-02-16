# Copyright (C) 2021 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later
from unittest import mock

from mantidimaging.eyes_tests.base_eyes import BaseEyesTest, LOAD_SAMPLE


class LoadDialogTest(BaseEyesTest):
    def test_load_dialog_opens(self):
        self.imaging.actionLoadDataset.trigger()

        self.check_target(widget=self.imaging.load_dialogue)

    def test_load_dialog_selected_dataset(self):
        self.imaging.actionLoadDataset.trigger()
        self.imaging.load_dialogue.select_file = mock.MagicMock(return_value=LOAD_SAMPLE)

        self.imaging.load_dialogue.presenter.do_update_sample()

        self.check_target(widget=self.imaging.load_dialogue)
