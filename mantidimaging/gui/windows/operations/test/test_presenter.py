# Copyright (C) 2021 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later

import unittest
import numpy as np
from functools import partial

from unittest import mock
from unittest.mock import DEFAULT, Mock

from mantidimaging.core.operation_history.const import OPERATION_HISTORY, OPERATION_DISPLAY_NAME
from mantidimaging.gui.windows.main import MainWindowView
from mantidimaging.gui.windows.operations import FiltersWindowPresenter
from mantidimaging.gui.windows.operations.presenter import REPEAT_FLAT_FIELDING_MSG, FLAT_FIELDING
from mantidimaging.test_helpers.unit_test_helper import assert_called_once_with, generate_images


class FiltersWindowPresenterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.main_window = mock.create_autospec(MainWindowView)
        self.main_window.filter_applied.connect = mock.Mock()
        self.view = mock.MagicMock()
        self.presenter = FiltersWindowPresenter(self.view, self.main_window)
        self.presenter.model.filter_widget_kwargs = {"roi_field": None}
        self.view.presenter = self.presenter

    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowModel.filter_registration_func')
    def test_register_active_filter(self, filter_reg_mock: mock.Mock):
        reg_fun_mock = mock.Mock()
        filter_reg_mock.return_value = reg_fun_mock
        self.view.filterSelector.currentIndex.return_value = 0
        self.presenter.do_register_active_filter()

        reg_fun_mock.assert_called_once()
        filter_reg_mock.assert_called_once()
        self.view.previews.link_before_after_histogram_scales.assert_called_once()

    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowModel.filter_registration_func')
    def test_link_before_after_histograms(self, _):
        self.view.filterSelector.currentText.return_value = "Clip Values"
        self.presenter.do_register_active_filter()

        self.view.previews.link_before_after_histogram_scales.assert_called_once_with(True)

    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowModel.filter_registration_func')
    def test_disconnect_before_after_histograms(self, _):
        self.view.filterSelector.currentText.return_value = "Rescale"
        self.presenter.do_register_active_filter()

        self.view.previews.link_before_after_histogram_scales.assert_called_once_with(False)

    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowModel.do_apply_filter')
    def test_apply_filter(self, apply_filter_mock: mock.Mock):
        stack = mock.Mock()
        presenter = mock.Mock()
        stack.presenter = presenter
        presenter.images.has_proj180deg.return_value = False
        self.presenter.stack = stack
        self.presenter.view.safeApply.isChecked.return_value = False
        self.presenter.do_apply_filter()

        expected_apply_to = [stack]
        assert_called_once_with(apply_filter_mock, expected_apply_to,
                                partial(self.presenter._post_filter, expected_apply_to))

    @mock.patch("mantidimaging.gui.windows.operations.presenter.operation_in_progress")
    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowModel.do_apply_filter')
    def test_apply_filter_to_all(self, apply_filter_mock: mock.Mock, _):
        self.view.ask_confirmation.return_value = False
        self.presenter.do_apply_filter_to_all()

        self.view.ask_confirmation.assert_called_once()

        self.view.ask_confirmation.reset_mock()
        self.view.ask_confirmation.return_value = True
        mock_stack_visualisers = [mock.Mock(), mock.Mock()]
        self.presenter._main_window = mock.Mock()
        self.presenter._main_window.get_all_stack_visualisers = mock.Mock()
        self.presenter._main_window.get_all_stack_visualisers.return_value = mock_stack_visualisers

        self.presenter.do_apply_filter_to_all()

        assert_called_once_with(apply_filter_mock, mock_stack_visualisers,
                                partial(self.presenter._post_filter, mock_stack_visualisers))

    @mock.patch.multiple('mantidimaging.gui.windows.operations.presenter.FiltersWindowPresenter',
                         do_update_previews=DEFAULT,
                         _wait_for_stack_choice=DEFAULT,
                         _do_apply_filter_sync=DEFAULT)
    def test_post_filter_success(self,
                                 do_update_previews: Mock = Mock(),
                                 _wait_for_stack_choice: Mock = Mock(),
                                 _do_apply_filter_sync: Mock = Mock()):
        """
        Tests when the operation has applied successfully.
        """
        self.presenter.view.safeApply.isChecked.return_value = False
        mock_stack_visualisers = [mock.Mock(), mock.Mock()]
        mock_task = mock.Mock()
        mock_task.error = None
        self.presenter._post_filter(mock_stack_visualisers, mock_task)

        do_update_previews.assert_called_once()
        _wait_for_stack_choice.assert_not_called()
        self.assertEqual(2, _do_apply_filter_sync.call_count)

        self.view.clear_notification_dialog.assert_called_once()
        self.view.show_operation_completed.assert_called_once_with(self.presenter.model.selected_filter.filter_name)

    @mock.patch.multiple('mantidimaging.gui.windows.operations.presenter.FiltersWindowPresenter',
                         do_update_previews=DEFAULT,
                         _do_apply_filter=DEFAULT)
    def test_post_filter_fail(self, do_update_previews: Mock = Mock(), _do_apply_filter: Mock = Mock()):
        """
        Tests when the operation has encountered an error.
        """
        self.presenter.view.safeApply.isChecked.return_value = False
        self.presenter.view.show_error_dialog = mock.Mock()  # type: ignore
        self.presenter.main_window.presenter = mock.Mock()
        mock_stack_visualisers = [mock.Mock()]
        mock_task = mock.Mock()
        mock_task.error = 123
        self.presenter._post_filter(mock_stack_visualisers, mock_task)

        self.presenter.view.show_error_dialog.assert_called_once_with('Operation failed: 123')
        do_update_previews.assert_called_once()
        self.presenter.main_window.presenter.model.set_images_in_stack.assert_called_once()

    @mock.patch.multiple(
        'mantidimaging.gui.windows.operations.presenter.FiltersWindowPresenter',
        _do_apply_filter=DEFAULT,
        _do_apply_filter_sync=DEFAULT,
    )
    def test_images_with_180_deg_proj_calls_filter_on_the_180_deg(self,
                                                                  _do_apply_filter: Mock = Mock(),
                                                                  _do_apply_filter_sync: Mock = Mock()):
        """
        Test that when an `Images` stack is encountered which also has a
        180deg projection stack reference, that 180deg stack is also processed
        with the same operation, to ensure consistency between the two images
        """
        self.presenter.view.safeApply.isChecked.return_value = False
        self.presenter.applying_to_all = False
        mock_stack = mock.MagicMock()
        mock_stack.presenter.images.has_proj180deg.return_value = True
        mock_stack_visualisers = [mock_stack]
        mock_task = mock.MagicMock()
        mock_task.error = None

        self.presenter._post_filter(mock_stack_visualisers, mock_task)

        _do_apply_filter.assert_not_called()
        _do_apply_filter_sync.assert_called_once()

    def test_update_previews_no_stack(self):
        self.presenter.do_update_previews()
        self.view.clear_previews.assert_called_once()

    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowModel.apply_to_images')
    def test_update_previews_apply_throws_exception(self, apply_mock: mock.Mock):
        apply_mock.side_effect = Exception
        stack = mock.Mock()
        presenter = mock.Mock()
        stack.presenter = presenter
        images = generate_images()
        presenter.get_image.return_value = images
        self.presenter.stack = stack

        self.presenter.do_update_previews()

        presenter.get_image.assert_called_once_with(self.presenter.model.preview_image_idx)
        self.view.clear_previews.assert_called_once()
        apply_mock.assert_called_once()

    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowPresenter._update_preview_image')
    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowModel.apply_to_images')
    def test_update_previews_with_no_lock_checked(self, apply_mock: mock.Mock, update_preview_image_mock: mock.Mock):
        stack = mock.Mock()
        presenter = mock.Mock()
        stack.presenter = presenter
        images = generate_images()
        presenter.get_image.return_value = images
        self.presenter.stack = stack
        self.view.lockZoomCheckBox.isChecked.return_value = False
        self.view.lockScaleCheckBox.isChecked.return_value = False
        self.presenter.do_update_previews()

        presenter.get_image.assert_called_once_with(self.presenter.model.preview_image_idx)
        self.view.clear_previews.assert_called_once()
        self.assertEqual(3, update_preview_image_mock.call_count)
        apply_mock.assert_called_once()
        self.view.previews.auto_range.assert_called_once()
        self.view.previews.record_histogram_regions.assert_not_called()
        self.view.previews.restore_histogram_regions.assert_not_called()

    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowPresenter._update_preview_image')
    @mock.patch('mantidimaging.gui.windows.operations.presenter.FiltersWindowModel.apply_to_images')
    def test_auto_range_called_when_locks_are_checked(self, apply_mock: mock.Mock,
                                                      update_preview_image_mock: mock.Mock):
        stack = mock.Mock()
        presenter = mock.Mock()
        stack.presenter = presenter
        images = generate_images()
        presenter.get_image.return_value = images
        self.presenter.stack = stack
        self.view.lockZoomCheckBox.isChecked.return_value = True
        self.view.lockScaleCheckBox.isChecked.return_value = True
        self.presenter.do_update_previews()

        self.view.previews.auto_range.assert_not_called()
        self.view.previews.record_histogram_regions.assert_called_once()
        self.view.previews.restore_histogram_regions.assert_called_once()

    def test_get_filter_module_name(self):
        self.presenter.model.filters = mock.MagicMock()

        module_name = self.presenter.get_filter_module_name(0)

        self.assertEqual("unittest.mock", module_name)

    @mock.patch.multiple(
        'mantidimaging.gui.windows.operations.presenter.FiltersWindowPresenter',
        _do_apply_filter=DEFAULT,
        _do_apply_filter_sync=DEFAULT,
    )
    @mock.patch('mantidimaging.gui.windows.operations.presenter.StackChoicePresenter')
    def test_safe_apply_starts_stack_choice_presenter(self,
                                                      stack_choice_presenter: Mock,
                                                      _do_apply_filter: Mock = Mock(),
                                                      _do_apply_filter_sync: Mock = Mock()):
        task = Mock()
        task.error = None

        self.presenter.view.safeApply.isChecked.return_value = True
        stack_choice_presenter.done = True
        self.presenter._do_apply_filter = mock.MagicMock()  # type: ignore
        task = mock.MagicMock()
        task.error = None

        self.presenter._post_filter([mock.MagicMock(), mock.MagicMock()], task)

        self.assertEqual(2, stack_choice_presenter.call_count)
        self.assertEqual(2, stack_choice_presenter.return_value.show.call_count)

    @mock.patch('mantidimaging.gui.windows.operations.presenter.StackChoicePresenter')
    def test_unchecked_safe_apply_does_not_start_stack_choice_presenter(self, stack_choice_presenter):
        self.presenter.view.safeApply.isChecked.return_value = False
        stack_choice_presenter.done = True
        self.presenter.applying_to_all = True
        self.presenter._do_apply_filter = mock.MagicMock()
        task = mock.MagicMock()
        task.error = None
        self.presenter._post_filter([mock.MagicMock(), mock.MagicMock()], task)

        stack_choice_presenter.assert_not_called()

    @mock.patch("mantidimaging.gui.windows.operations.presenter.operation_in_progress")
    def test_original_stack_assigned_when_safe_apply_checked(self, _):
        stack = mock.MagicMock()
        self.presenter.stack = stack
        stack_data = "THIS IS USEFUL STACK DATA"
        stack.presenter.images.copy.return_value = stack_data
        self.presenter._do_apply_filter = mock.MagicMock()

        self.presenter.do_apply_filter()

        stack.presenter.images.copy.assert_called_once()
        self.assertEqual(stack_data, self.presenter.original_images_stack)

    def test_set_filter_by_name(self):
        NAME = "ROI Normalisation"
        INDEX = 3
        self.presenter.model._find_filter_index_from_filter_name = mock.Mock(return_value=INDEX)
        self.presenter.set_filter_by_name(NAME)

        self.presenter.model._find_filter_index_from_filter_name.assert_called_with(NAME)
        self.view.filterSelector.setCurrentIndex.assert_called_with(INDEX)

    @mock.patch("mantidimaging.gui.windows.operations.presenter.operation_in_progress")
    def test_warning_when_flat_fielding_is_run_twice(self, _):
        """
        Test that a warning is displayed if the user is trying to run flat-fielding again.
        """
        self.view.filterSelector.currentText.return_value = FLAT_FIELDING
        self.presenter.stack = mock.MagicMock()
        self.presenter.stack.presenter.images.metadata = {
            OPERATION_HISTORY: [{
                OPERATION_DISPLAY_NAME: "Flat-fielding"
            }]
        }
        self.presenter._do_apply_filter = mock.MagicMock()
        self.presenter.do_apply_filter()
        self.view.ask_confirmation.assert_called_once_with(REPEAT_FLAT_FIELDING_MSG)

    @mock.patch("mantidimaging.gui.windows.operations.presenter.operation_in_progress")
    def test_no_warning_when_flat_fielding_isnt_run(self, _):
        """
        Test no warning is created if the user isn't running flat fielding.
        """
        self.view.filterSelector.currentText.return_value = "Median"
        self.presenter.stack = mock.MagicMock()
        self.presenter._do_apply_filter = mock.MagicMock()
        self.presenter.do_apply_filter()
        self.view.ask_confirmation.assert_not_called()

    @mock.patch("mantidimaging.gui.windows.operations.presenter.operation_in_progress")
    def test_no_warning_when_flat_fielding_is_first_operation(self, _):
        """
        Test that no warning is created when flat fielding is the first operation the user runs, and no operation
        history exists.
        """
        self.view.filterSelector.currentText.return_value = FLAT_FIELDING
        self.presenter.stack = mock.MagicMock()
        self.presenter._do_apply_filter = mock.MagicMock()
        self.presenter.do_apply_filter()
        self.view.ask_confirmation.assert_not_called()

    @mock.patch("mantidimaging.gui.windows.operations.presenter.operation_in_progress")
    def test_no_warning_when_flat_fielding_is_run_for_first_time(self, _):
        """
        Test that no warning is created if an operation history exists but flat fielding isn't in it.
        """
        self.view.filterSelector.currentText.return_value = FLAT_FIELDING
        self.presenter.stack = mock.MagicMock()
        self.presenter.stack.presenter.images.metadata = {
            OPERATION_HISTORY: [{
                OPERATION_DISPLAY_NAME: "Remove Outliers"
            }]
        }
        self.presenter._do_apply_filter = mock.MagicMock()
        self.presenter.do_apply_filter()
        self.view.ask_confirmation.assert_not_called()

    @mock.patch("mantidimaging.gui.windows.operations.presenter.operation_in_progress")
    def test_no_operation_run_when_user_cancels_flat_fielding(self, _):
        """
        Test that pressing "Cancel" when the flat-fielding warning is displayed means that no operation is run.
        """
        self.view.filterSelector.currentText.return_value = FLAT_FIELDING
        self.presenter.stack = mock.MagicMock()
        self.presenter.stack.presenter.images.metadata = {
            OPERATION_HISTORY: [{
                OPERATION_DISPLAY_NAME: "Flat-fielding"
            }]
        }
        self.presenter._do_apply_filter = mock.MagicMock()
        self.view.ask_confirmation.return_value = False
        self.presenter.do_apply_filter()
        self.presenter._do_apply_filter.assert_not_called()

    @mock.patch("mantidimaging.gui.windows.operations.presenter.operation_in_progress")
    def test_buttons_disabled_while_filter_is_running(self, _):
        self.presenter.model.do_apply_filter = mock.MagicMock()
        self.presenter._do_apply_filter(None)
        self.presenter.view.applyButton.setEnabled.assert_called_once_with(False)
        self.presenter.view.applyToAllButton.setEnabled.assert_called_once_with(False)

    @mock.patch("mantidimaging.gui.windows.operations.presenter.operation_in_progress")
    def test_running_operation_records_previous_button_states(self, _):
        self.presenter.view.applyButton.isEnabled.return_value = prev_apply_single_state = True
        self.presenter.view.applyToAllButton.isEnabled.return_value = prev_apply_all_state = False
        self.presenter.model.do_apply_filter = mock.MagicMock()
        self.presenter._do_apply_filter(None)
        assert self.presenter.prev_apply_single_state == prev_apply_single_state
        assert self.presenter.prev_apply_all_state == prev_apply_all_state

    def test_init_crop_coords_does_nothing_when_stack_is_none(self):
        mock_roi_field = mock.Mock()
        self.presenter.init_crop_coords(mock_roi_field)
        mock_roi_field.setText.assert_not_called()

    def test_init_crop_coords_does_nothing_when_image_is_greater_than_200_by_200(self):
        mock_roi_field = mock.Mock()
        self.presenter.stack = mock.Mock()
        self.presenter.stack.presenter.images.data = np.ones((3,201,201))
        self.presenter.init_crop_coords(mock_roi_field)
        mock_roi_field.setText.assert_not_called()