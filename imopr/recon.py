from __future__ import (absolute_import, division, print_function)
import numpy as np


def execute(sample, flat, dark, config, indices):
    from imopr import helper
    helper.print_start("Running IMOPR with action RECON")

    from recon.tools import tool_importer
    tool = tool_importer.do_importing(config.func.tool)

    inc = float(config.func.max_angle) / sample.shape[0]
    proj_angles = np.arange(0, sample.shape[0] * inc, inc)
    proj_angles = np.radians(proj_angles)

    from imopr.sinogram import make_sinogram
    sample = make_sinogram(sample)
    from imopr.visualiser import show_3d

    i1, i2 = helper.handle_indices(indices)

    sample = tool.run_reconstruct(
        sample[i1:i2, :, :],
        config,
        config.helper,
        sinogram_order=True,
        proj_angles=proj_angles)

    from imopr.visualiser import show_3d
    show_3d(sample, 0)

    # stop python from exiting
    import matplotlib.pyplot as plt
    plt.show()

    return sample
