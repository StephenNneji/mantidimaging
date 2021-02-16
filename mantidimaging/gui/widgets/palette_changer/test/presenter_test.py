# Copyright (C) 2021 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later

import unittest
from unittest import mock

import numpy as np

from mantidimaging.gui.widgets.palette_changer.presenter import PaletteChangerPresenter, RANDOM_CUTOFF


def _normalise_break_value(break_value, min_value, max_value):
    return (break_value - min_value) / abs(max_value - min_value)


def _normalise_break_values(break_vals, min_value, max_value):
    return list(
        map(lambda break_value: _normalise_break_value(break_value, min_value=min_value, max_value=max_value),
            break_vals))


class PaletteChangerPresenterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.view = mock.MagicMock()
        self.histograms = [mock.Mock() for _ in range(3)]
        self.recon_histogram = self.histograms[0]
        self.recon_image = np.random.random((200, 200))
        self.recon_gradient = self.recon_histogram.gradient
        self.presenter = PaletteChangerPresenter(self.view, self.histograms, self.recon_image)

    def get_sorted_random_elements_from_projection_image(self, n_vals: int):
        return sorted([np.random.choice(self.presenter.flattened_image) for _ in range(n_vals)])

    def test_flattened_image_creation_for_large_image(self):
        assert self.presenter.flattened_image.size == RANDOM_CUTOFF
        assert self.presenter.flattened_image.ndim == 1

    def test_flattened_image_creation_for_small_image(self):
        presenter = PaletteChangerPresenter(self.view, self.histograms, np.random.random((20, 20)))
        assert presenter.flattened_image.size == 400
        assert presenter.flattened_image.ndim == 1

    def test_change_colour_map(self):
        self.view.colour_map = colour_map_selection = "acolourmap"
        self.presenter._change_colour_map()

        for histogram in self.histograms:
            histogram.gradient.loadPreset.assert_called_once_with(colour_map_selection)

    def test_record_old_tick_points(self):
        old_ticks_list = [mock.Mock() for i in range(2)]
        self.recon_histogram.gradient.ticks = {old_ticks_list[i]: i * 1.0 for i in range(2)}
        self.presenter._record_old_tick_points()
        self.assertListEqual(self.presenter.old_ticks, old_ticks_list)

    def test_insert_new_ticks(self):
        tick_locations = [i * 0.1 for i in range(11)]
        self.presenter._insert_new_ticks(tick_locations)
        self.recon_gradient.addTick.assert_has_calls(
            [mock.call(x, color=self.recon_gradient.getColor.return_value, finish=False) for x in tick_locations])

    def test_get_colours(self):
        get_color_mock = self.recon_histogram.gradient.getColor
        n_ticks = 5
        colours = self.presenter._get_colours(n_ticks)
        get_color_mock.assert_has_calls([mock.call(x) for x in np.linspace(0, 1, n_ticks)])
        for colour in colours:
            assert colour == get_color_mock.return_value

    @mock.patch("mantidimaging.gui.widgets.palette_changer.presenter.filters.threshold_multiotsu")
    def test_generate_otsu_tick_points(self, threshold_otsu_mock):
        self.view.num_materials = n_materials = 4
        threshold_otsu_mock.return_value = otsu_values = np.array(
            self.get_sorted_random_elements_from_projection_image(n_materials + 1))
        norm_otsu = _normalise_break_values(otsu_values, self.recon_image.min(), self.recon_image.max())
        self.assertListEqual(self.presenter._generate_otsu_tick_points(), [0.0] + norm_otsu + [1.0])

    @mock.patch("mantidimaging.gui.widgets.palette_changer.presenter.jenks_breaks")
    def test_generate_jenks_tick_points(self, jenks_break_mocks):
        self.view.num_materials = n_materials = 4
        jenks_break_mocks.return_value = expected_jenks_ticks = self.get_sorted_random_elements_from_projection_image(
            n_materials + 1)
        expected_jenks_ticks = _normalise_break_values(expected_jenks_ticks, self.recon_image.min(),
                                                       self.recon_image.max())
        expected_jenks_ticks[0] = 0.0
        expected_jenks_ticks[-1] = 1.0
        actual_tick_points = self.presenter._generate_jenks_tick_points()
        jenks_break_mocks.assert_called_once_with(self.presenter.flattened_image, n_materials)
        self.assertListEqual(expected_jenks_ticks, actual_tick_points)

    def test_remove_old_ticks(self):
        n_old_ticks = 3
        self.presenter.old_ticks = mock_old_ticks = [mock.Mock() for _ in range(n_old_ticks)]
        self.presenter._remove_old_ticks()
        self.recon_gradient.removeTick.assert_has_calls([mock.call(t, finish=False) for t in mock_old_ticks])

    def test_update_ticks(self):
        self.presenter._update_ticks()
        self.recon_gradient.showTicks.assert_called_once()
        self.recon_gradient.updateGradient.assert_called_once()
        self.recon_gradient.sigGradientChangeFinished.emit.assert_called_once_with(self.recon_gradient)

    @mock.patch("mantidimaging.gui.widgets.palette_changer.presenter.jenks_breaks")
    def test_change_colour_palette_changes_ticks(self, jenks_breaks_mock):
        n_old_ticks = 3
        old_ticks_list = [mock.Mock() for _ in range(n_old_ticks)]
        new_ticks_list = []
        self.recon_gradient.ticks = {old_ticks_list[i]: i * 0.5 for i in range(n_old_ticks)}

        def add_tick_side_effect(location, color, finish):
            new_tick = mock.Mock()
            self.recon_gradient.ticks[new_tick] = location
            new_ticks_list.append(new_tick)

        def remove_tick_side_effect(tick, finish):
            del self.recon_gradient.ticks[tick]

        self.recon_gradient.addTick = mock.Mock(side_effect=add_tick_side_effect)
        self.recon_gradient.removeTick = mock.Mock(side_effect=remove_tick_side_effect)

        self.view.algorithm = "Jenks"
        self.view.num_materials = n_materials = 4
        jenks_breaks_mock.return_value = self.get_sorted_random_elements_from_projection_image(n_materials + 1)

        self.presenter.change_colour_palette()

        for old_tick in old_ticks_list:
            self.assertNotIn(old_tick, self.recon_gradient.ticks.keys())
        for new_tick in new_ticks_list:
            self.assertIn(new_tick, self.recon_gradient.ticks.keys())

        assert n_materials + 1 == len(self.recon_gradient.ticks.keys())
