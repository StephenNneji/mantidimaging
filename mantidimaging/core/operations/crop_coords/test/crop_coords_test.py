# Copyright (C) 2021 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later

import unittest

from unittest import mock
import numpy.testing as npt

import mantidimaging.test_helpers.unit_test_helper as th
from mantidimaging.core.operations.crop_coords import CropCoordinatesFilter
from mantidimaging.core.utility.memory_usage import get_memory_usage_linux
from mantidimaging.core.utility.sensible_roi import SensibleROI


class CropCoordsTest(unittest.TestCase):
    """
    Test crop by coordinates filter.

    Tests return value only.
    """
    def __init__(self, *args, **kwargs):
        super(CropCoordsTest, self).__init__(*args, **kwargs)

    def test_executed_only_volume(self):
        # Check that the filter is  executed when:
        #   - valid Region of Interest is provided
        #   - no flat or dark images are provided

        roi = SensibleROI.from_list([1, 1, 5, 5])
        images = th.generate_images()
        # store a reference here so it doesn't get freed inside the filter execute
        sample = images.data
        result = CropCoordinatesFilter.filter_func(images, roi)
        expected_shape = (10, 4, 4)

        npt.assert_equal(result.data.shape, expected_shape)
        # check that the data has been modified
        th.assert_not_equals(result.data, sample)

    def test_memory_change_acceptable(self):
        """
        Expected behaviour for the filter is to be done in place
        without using more memory.

        In reality the memory is increased by about 40MB (4 April 2017),
        but this could change in the future.

        The reason why a 10% window is given on the expected size is
        to account for any library imports that may happen.

        This will still capture if the data is doubled, which is the main goal.
        """
        images = th.generate_images()
        roi = SensibleROI.from_list([1, 1, 5, 5])

        cached_memory = get_memory_usage_linux(mb=True)[0]

        result = CropCoordinatesFilter.filter_func(images, roi)

        self.assertLess(get_memory_usage_linux(mb=True)[0], cached_memory * 1.1)

        expected_shape = (10, 4, 4)

        npt.assert_equal(result.data.shape, expected_shape)

    def test_execute_wrapper_return_is_runnable(self):
        """
        Test that the partial returned by execute_wrapper can be executed (kwargs are named correctly)
        """
        images = th.generate_images()
        roi_mock = mock.Mock()
        roi_mock.text.return_value = "0, 0, 5, 5"
        CropCoordinatesFilter.execute_wrapper(roi_mock)(images)
        roi_mock.text.assert_called_once()

    def test_execute_wrapper_bad_roi_raises_valueerror(self):
        """
        Test that the partial returned by execute_wrapper can be executed (kwargs are named correctly)
        """
        roi_mock = mock.Mock()
        roi_mock.text.return_value = "apples"
        self.assertRaises(ValueError, CropCoordinatesFilter.execute_wrapper, roi_mock)
        roi_mock.text.assert_called_once()


if __name__ == '__main__':
    unittest.main()
