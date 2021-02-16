# Copyright (C) 2021 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later

import unittest
from unittest import mock

import numpy as np
import numpy.testing as npt

import mantidimaging.test_helpers.unit_test_helper as th
from mantidimaging.core.data.images import Images
from mantidimaging.core.operations.roi_normalisation import RoiNormalisationFilter
from mantidimaging.core.utility.sensible_roi import SensibleROI


class ROINormalisationTest(unittest.TestCase):
    """
    Test contrast ROI normalisation filter.

    Tests return value and in-place modified data.
    """
    def __init__(self, *args, **kwargs):
        super(ROINormalisationTest, self).__init__(*args, **kwargs)

    def test_not_executed_empty_params(self):
        images = th.generate_images()

        air = None

        original = np.copy(images.data[0])
        result = RoiNormalisationFilter.filter_func(images, air)
        npt.assert_equal(result.data[0], original)

    def test_not_executed_invalid_shape(self):
        images = np.arange(100).reshape(10, 10)
        air = [3, 3, 4, 4]
        npt.assert_raises(ValueError, RoiNormalisationFilter.filter_func, images, air)

    def test_executed_par(self):
        self.do_execute(th.generate_images_for_parallel())

    def test_executed_seq(self):
        self.do_execute(th.generate_images())

    def do_execute(self, images: Images):
        original = np.copy(images.data[0])

        air = SensibleROI.from_list([3, 3, 4, 4])
        result = RoiNormalisationFilter.filter_func(images, air)

        th.assert_not_equals(result.data[0], original)

    def test_execute_wrapper_return_is_runnable(self):
        """
        Test that the partial returned by execute_wrapper can be executed (kwargs are named correctly)
        """
        images = th.generate_images()
        roi_mock = mock.Mock()
        roi_mock.text.return_value = "0, 0, 5, 5"
        RoiNormalisationFilter.execute_wrapper(roi_mock)(images)
        roi_mock.text.assert_called_once()

    def test_roi_normalisation_performs_rescale(self):
        images = th.generate_images()
        images_max = images.data.max()

        original = np.copy(images.data[0])
        air = [3, 3, 4, 4]
        result = RoiNormalisationFilter.filter_func(images, air)

        th.assert_not_equals(result.data[0], original)
        self.assertAlmostEqual(result.data.max(), images_max, places=6)

    def test_execute_wrapper_bad_roi_raises_valueerror(self):
        """
        Test that the partial returned by execute_wrapper can be executed (kwargs are named correctly)
        """
        roi_mock = mock.Mock()
        roi_mock.text.return_value = "apples"
        self.assertRaises(ValueError, RoiNormalisationFilter.execute_wrapper, roi_mock)
        roi_mock.text.assert_called_once()


if __name__ == '__main__':
    unittest.main()
