# Copyright (C) 2021 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later

import os
import unittest
import getpass
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMainWindow, QMenu, QWidget, QApplication
from applitools.common import MatchLevel

from mantidimaging.core.io.loader import loader
from mantidimaging.eyes_tests.eyes_manager import EyesManager
from mantidimaging.test_helpers.start_qapplication import start_qapplication

# APPLITOOLS_BATCH_ID will be set by Github actions to the commit SHA, or a random UUID for individual developer
# execution

APPLITOOLS_BATCH_ID = os.getenv("APPLITOOLS_BATCH_ID")
if APPLITOOLS_BATCH_ID is None:
    APPLITOOLS_BATCH_ID = str(uuid4())

API_KEY_PRESENT = os.getenv("APPLITOOLS_API_KEY")
if API_KEY_PRESENT is None:
    raise unittest.SkipTest("API Key is not defined in the environment, so Eyes tests are skipped.")

TEST_NAME = os.getenv("GITHUB_BRANCH_NAME")
if TEST_NAME is None:
    TEST_NAME = f"{getpass.getuser()}'s Local Test"

LOAD_SAMPLE = str(Path.home()) + "/mantidimaging-data/ISIS/IMAT/IMAT00010675/Tomo/IMAT_Flower_Tomo_000000.tif"
if not os.path.exists(LOAD_SAMPLE):
    raise unittest.SkipTest(
        "Data not present, please clone to your home directory e.g. git clone https://github.com/mantidproject/mantidim"
        "aging-data.git ~/mantidimaging-data")

QApplication.setFont(QFont("Sans Serif", 10))


@start_qapplication
class BaseEyesTest(unittest.TestCase):
    eyes_manager: EyesManager

    @classmethod
    def setUpClass(cls) -> None:
        cls.eyes_manager = EyesManager("Mantid Imaging", test_name=TEST_NAME)
        cls.eyes_manager.set_batch(APPLITOOLS_BATCH_ID)

    def setUp(self):
        self.eyes_manager.set_match_level(MatchLevel.LAYOUT)

        self.imaging = None
        self.eyes_manager.image_directory = mkdtemp()

        self.stacks = []

        # Do setup
        self.eyes_manager.start_imaging()

    def tearDown(self):
        if self.imaging is not None:
            self.eyes_manager.close_imaging()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.eyes_manager.close_eyes()

    @property
    def imaging(self):
        return self.eyes_manager.imaging

    @imaging.setter
    def imaging(self, imaging):
        self.eyes_manager.imaging = imaging

    def check_target(self, image=None, widget: QWidget = None):
        self.eyes_manager.check_target(image, widget)

    @staticmethod
    def show_menu(widget: QMainWindow, menu: QMenu):
        menu_location = widget.menuBar().rect().bottomLeft()
        menu.popup(widget.mapFromGlobal(menu_location))

    def _load_data_set(self):
        dataset = loader.load(file_names=[LOAD_SAMPLE])
        dock, vis = self.imaging.presenter.create_new_stack(dataset, "Stack 1")

        QApplication.sendPostedEvents()

        return dock, vis
