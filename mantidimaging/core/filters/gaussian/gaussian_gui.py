from functools import partial

from mantidimaging.core.algorithms import gui_compile_ui as gcu
from mantidimaging.gui.algorithm_dialog import AlgorithmDialog

from . import gaussian

GUI_MENU_NAME = "Gaussian Filter"


def _gui_register(main_window):
    from PyQt5 import Qt
    dialog = AlgorithmDialog(main_window)
    dialog.setWindowTitle(GUI_MENU_NAME)

    label_size = Qt.QLabel("Kernel Size")
    size_field = Qt.QSpinBox()
    size_field.setMinimum(0)
    size_field.setMaximum(1000)
    size_field.setValue(3)

    order_field = Qt.QSpinBox()
    order_field.setMinimum(0)
    order_field.setMaximum(3)
    order_field.setValue(0)

    label_mode = Qt.QLabel("Mode")
    mode_field = Qt.QComboBox()
    mode_field.addItems(gaussian.modes())

    dialog.formLayout.addRow(label_size, size_field)
    dialog.formLayout.addRow(label_mode, mode_field)

    def custom_execute():
        return partial(
            gaussian.execute,
            size=size_field.value(),
            mode=mode_field.currentText(),
            order=order_field.value())

    # replace dialog function with this one
    dialog.set_execute(custom_execute)
    return dialog
