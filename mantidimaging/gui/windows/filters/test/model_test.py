import unittest
from functools import partial

import mock
import numpy as np

import mantidimaging.test_helpers.unit_test_helper as th
from mantidimaging.gui.windows.filters import FiltersWindowModel
from mantidimaging.gui.windows.stack_visualiser import (
    StackVisualiserView, StackVisualiserPresenter, SVParameters)


class FiltersWindowModelTest(unittest.TestCase):
    APPLY_BEFORE_AFTER_MAGIC_NUMBER = 42
    ROI_PARAMETER = (4, 3, 2, 1)

    def __init__(self, *args, **kwargs):
        super(FiltersWindowModelTest, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        cls.test_data = th.generate_images_class_random_shared_array()

    def setUp(self):
        self.sv_view = mock.create_autospec(StackVisualiserView)
        self.sv_view.current_roi = self.ROI_PARAMETER

        self.sv_presenter = StackVisualiserPresenter(
            self.sv_view, self.test_data)
        self.sv_view.presenter = self.sv_presenter

        self.model = FiltersWindowModel()

    def execute_mock(self, data):
        self.assertTrue(isinstance(data, np.ndarray))
        data *= 4
        return data

    def execute_mock_with_roi(self, data, roi):
        self.assertTrue(isinstance(data, np.ndarray))
        data *= 4
        self.assertEquals(roi, self.ROI_PARAMETER)
        return data

    def apply_before_mock(self, data):
        self.assertTrue(isinstance(data, np.ndarray))
        self.apply_before_mock_variable = \
            self.APPLY_BEFORE_AFTER_MAGIC_NUMBER
        return self.apply_before_mock_variable

    def apply_after_mock(self, data, result_from_before):
        self.assertTrue(isinstance(data, np.ndarray))
        self.assertEqual(result_from_before,
                         self.APPLY_BEFORE_AFTER_MAGIC_NUMBER)

    def test_filters_populated(self):
        self.assertTrue(len(self.model.filter_names) > 0)

    def test_do_apply_filter(self):
        self.model.stack = self.sv_presenter.view

        execute = mock.Mock(return_value=partial(self.execute_mock))

        self.model.setup_filter((None, None, execute, None))
        self.model.do_apply_filter()

        execute.assert_called_once()

    def test_do_apply_filter_with_roi(self):
        self.model.stack = self.sv_presenter.view

        execute = mock.MagicMock(return_value=partial(self.execute_mock_with_roi))

        params = {
            'roi': SVParameters.ROI
        }

        self.model.setup_filter((params, None, execute, None))
        self.model.do_apply_filter()

        execute.assert_called_once()

    def test_do_apply_filter_pre_post_processing(self):
        self.model.stack = self.sv_presenter.view

        execute = mock.MagicMock(return_value=partial(self.execute_mock))

        do_before = mock.MagicMock(return_value=partial(self.apply_before_mock))
        do_after = mock.MagicMock(return_value=partial(self.apply_after_mock))

        self.model.setup_filter((None, do_before, execute, do_after))
        self.model.do_apply_filter()

        execute.assert_called_once()

        do_before.assert_called_once()
        do_after.assert_called_once()


if __name__ == '__main__':
    unittest.main()
