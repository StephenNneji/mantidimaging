# Copyright (C) 2021 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later
from math import isnan
from typing import Tuple, Optional

import numpy
from PyQt6 import QtCore
from pyqtgraph import GraphicsLayoutWidget, ImageItem, ViewBox, HistogramLUTItem, LabelItem, InfiniteLine

from mantidimaging.core.utility.close_enough_point import CloseEnoughPoint
from mantidimaging.core.utility.data_containers import Degrees
from mantidimaging.core.utility.histogram import set_histogram_log_scale


class ReconImagesView(GraphicsLayoutWidget):
    sigSliceIndexChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.projection, self.projection_vb, self.projection_hist = self.image_in_vb("Projection")
        self.sinogram, self.sinogram_vb, self.sinogram_hist = self.image_in_vb("Sinogram")
        self.recon, self.recon_vb, self.recon_hist = self.image_in_vb("Recon")

        self.slice_line = InfiniteLine(pos=1024, angle=0, bounds=[0, self.projection.width()], movable=True)
        self.projection_vb.addItem(self.slice_line)
        self.tilt_line = InfiniteLine(pos=1024, angle=90, pen=(255, 0, 0, 255), movable=True)

        image_layout = self.addLayout(colspan=4)
        image_layout.addItem(self.projection_vb, 0, 0)
        image_layout.addItem(self.projection_hist, 0, 1)
        image_layout.addItem(self.recon_vb, 0, 2, rowspan=3)
        image_layout.addItem(self.recon_hist, 0, 3, rowspan=3)

        projection_details = LabelItem("Value")
        image_layout.addItem(projection_details, 1, 0, 1, 2)

        image_layout.addItem(self.sinogram_vb, 2, 0)
        image_layout.addItem(self.sinogram_hist, 2, 1)
        sino_details = LabelItem("Value")
        image_layout.addItem(sino_details, 3, 0, 1, 2)
        recon_details = LabelItem("Value")
        image_layout.addItem(recon_details, 3, 2, 1, 2)

        msg_format = "Value: {:.6f}"
        self.display_formatted_detail = {
            self.projection: lambda val: projection_details.setText(msg_format.format(val)),
            self.sinogram: lambda val: sino_details.setText(msg_format.format(val)),
            self.recon: lambda val: recon_details.setText(msg_format.format(val))
        }
        self.projection.hoverEvent = lambda ev: self.mouse_over(ev, self.projection)
        self.projection.mouseClickEvent = lambda ev: self.mouse_click(ev, self.slice_line)
        self.slice_line.sigPositionChangeFinished.connect(self.slice_line_moved)
        self.sinogram.hoverEvent = lambda ev: self.mouse_over(ev, self.sinogram)
        self.recon.hoverEvent = lambda ev: self.mouse_over(ev, self.recon)

        # Work around for https://github.com/mantidproject/mantidimaging/issues/565
        for scene in [
                self.projection.scene(),
                self.projection_hist.scene(),
                self.sinogram.scene(),
                self.sinogram_hist.scene(),
                self.recon.scene(),
                self.recon_hist.scene(),
        ]:
            scene.contextMenu = [item for item in scene.contextMenu if "export" not in item.text().lower()]

    def slice_line_moved(self):
        self.slice_changed(int(self.slice_line.value()))

    @staticmethod
    def image_in_vb(name=None) -> Tuple[ImageItem, ViewBox, HistogramLUTItem]:
        im = ImageItem()
        vb = ViewBox(invertY=True, lockAspect=True, name=name)
        vb.addItem(im)
        hist = HistogramLUTItem(im)
        return im, vb, hist

    def update_projection(self, image_data: numpy.ndarray, preview_slice_index: int, tilt_angle: Optional[Degrees]):
        self.projection.clear()
        self.projection.setImage(image_data)
        self.projection_hist.imageChanged(autoLevel=True, autoRange=True)
        self.slice_line.setPos(preview_slice_index)
        if tilt_angle:
            self.set_tilt(tilt_angle, image_data.shape[1] // 2)
        else:
            self.hide_tilt()
        set_histogram_log_scale(self.projection_hist)

    def update_sinogram(self, image):
        self.sinogram.clear()
        self.sinogram.setImage(image)
        self.sinogram_hist.imageChanged(autoLevel=True, autoRange=True)
        set_histogram_log_scale(self.sinogram_hist)

    def update_recon(self, image_data, refresh_recon_slice_histogram):
        self.recon.clear()
        self.recon.setImage(image_data, autoLevels=refresh_recon_slice_histogram)
        if refresh_recon_slice_histogram:
            self.recon_hist.imageChanged(autoLevel=True, autoRange=True)
        set_histogram_log_scale(self.recon_hist)

    def mouse_over(self, ev, img):
        # Ignore events triggered by leaving window or right clicking
        if ev.exit:
            return
        pos = CloseEnoughPoint(ev.pos())
        if img.image is not None and pos.x < img.image.shape[0] and pos.y < img.image.shape[1]:
            pixel_value = img.image[pos.y, pos.x]
            self.display_formatted_detail[img](pixel_value)

    def mouse_click(self, ev, line: InfiniteLine):
        line.setPos(ev.pos())
        self.slice_changed(CloseEnoughPoint(ev.pos()).y)

    def slice_changed(self, slice_index):
        # don't refresh the histogram on click to stop the contrast for re-adjusting for each slice
        # it's much easier to see what's happening to the reconstruction if the slice doesn't
        # reset after every click
        self.parent.presenter.do_preview_reconstruct_slice(slice_idx=slice_index, refresh_recon_slice_histogram=False)
        self.sigSliceIndexChanged.emit(slice_index)

    def clear_recon(self):
        self.recon.clear()

    def reset_slice_and_tilt(self, slice_index):
        self.slice_line.setPos(slice_index)
        self.hide_tilt()

    def hide_tilt(self):
        """
        Hides the tilt line. This stops infinite zooming out loop that messes up the image view
        (the line likes to be unbound when the degree isn't a multiple o 90 - and the tilt never is)
        :return:
        """
        self.projection_vb.removeItem(self.tilt_line)

    def set_tilt(self, tilt: Degrees, pos: Optional[int] = None):
        if not isnan(tilt.value):  # is isnan it means there is no tilt, i.e. the line is vertical
            if pos is not None:
                self.tilt_line.setAngle(90)
                self.tilt_line.setPos(pos)
            self.tilt_line.setAngle(90 + tilt.value)
        self.projection_vb.addItem(self.tilt_line)

    def reset_recon_histogram(self):
        self.recon_hist.autoHistogramRange()
