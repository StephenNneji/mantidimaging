# Copyright (C) 2020 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later

import unittest
from unittest import mock

import numpy.testing as npt
import numpy as np

import mantidimaging.test_helpers.unit_test_helper as th
from mantidimaging.core.data import Images
from mantidimaging.gui.windows.stack_visualiser import StackVisualiserPresenter, StackVisualiserView, SVNotification, \
    SVImageMode


class StackVisualiserPresenterTest(unittest.TestCase):
    test_data: Images

    def __init__(self, *args, **kwargs):
        super(StackVisualiserPresenterTest, self).__init__(*args, **kwargs)

    def setUp(self):
        self.test_data = th.generate_images()
        # mock the view so it has the same methods
        self.view = mock.create_autospec(StackVisualiserView)
        self.presenter = StackVisualiserPresenter(self.view, self.test_data)
        self.presenter.model = mock.Mock()

    def test_get_image(self):
        index = 3

        test_data = self.test_data

        img = self.presenter.get_image(index)
        npt.assert_equal(test_data.data[index], img.data[0])

    def test_delete_data(self):
        self.presenter.images = th.generate_images()
        self.presenter.delete_data()
        self.assertIsNone(self.presenter.images, None)

    def test_notify_refresh_image_normal_image_mode(self):
        self.presenter.image_mode = SVImageMode.NORMAL
        self.presenter.notify(SVNotification.REFRESH_IMAGE)
        self.assertIs(self.view.image, self.presenter.images.data, "Image should have been set as sample images")

    def test_notify_refresh_image_averaged_image_mode(self):
        self.presenter.image_mode = SVImageMode.SUMMED
        self.presenter.notify(SVNotification.REFRESH_IMAGE)
        self.assertIs(self.view.image, self.presenter.summed_image, "Image should have been set as averaged image")

    def test_notify_toggle_image_mode_normal_to_summed(self):
        self.presenter.image_mode = SVImageMode.SUMMED
        self.presenter.notify(SVNotification.TOGGLE_IMAGE_MODE)
        assert self.presenter.image_mode is SVImageMode.NORMAL
        self.presenter.model.sum_images.assert_not_called()

    def test_notify_toggle_image_mode_summed_to_normal(self):
        self.presenter.image_mode = SVImageMode.NORMAL
        self.presenter.notify(SVNotification.TOGGLE_IMAGE_MODE)
        assert self.presenter.image_mode is SVImageMode.SUMMED

    def test_notify_toggle_image_mode_sets_summed_image(self):
        self.presenter.image_mode = SVImageMode.NORMAL
        self.summed_image = None
        self.presenter.notify(SVNotification.TOGGLE_IMAGE_MODE)
        assert self.presenter.summed_image == self.presenter.model.sum_images.return_value
        self.presenter.model.sum_images.assert_called_once_with(self.presenter.images.data)

    def test_notify_toggle_image_mode_does_not_set_summed_image(self):
        self.presenter.image_mode = SVImageMode.NORMAL
        self.presenter.summed_image = self.presenter.images.data[0]
        self.presenter.notify(SVNotification.TOGGLE_IMAGE_MODE)
        self.presenter.model.sum_images.assert_not_called()

    def test_get_num_images(self):
        assert self.presenter.get_num_images() == self.presenter.images.num_projections

    def test_find_image_from_angle_returns_matching_index(self):
        angle_rad = self.presenter.images.projection_angles().value[1]
        angle_deg = np.rad2deg(angle_rad)
        index = self.presenter.find_image_from_angle(angle_deg)
        assert self.presenter.images.projection_angles().value[index] == angle_rad

    def test_find_image_from_angle_returns_next_index(self):
        angle = (self.presenter.images.projection_angles().value[1] +
                 self.presenter.images.projection_angles().value[2]) * 0.5
        angle = np.rad2deg(angle)
        index = self.presenter.find_image_from_angle(angle)
        assert index == 2


if __name__ == '__main__':
    unittest.main()
