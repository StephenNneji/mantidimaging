from __future__ import (absolute_import, division, print_function)
from mantidimaging import helper as h
from mantidimaging.core.tools import importer


def _cli_register(parser):
    parser.add_argument(
        "-log",
        "--minus-log",
        required=False,
        action='store_true',
        help="Calculate the -log of the sample data.")

    return parser


def execute(data, minus_log=True):
    """
    This filter should be used on transmission images (background corrected images).
    It converts the images from transmission to attenuation.

    :param data: Sample data which is to be processed. Expected in radiograms
    :param minus_log: Default True
                      Specify whether to calculate minus log or just return.
    """
    if minus_log:
        # import early to check if tomopy is available
        tomopy = importer.do_importing('tomopy')
        h.pstart("Calculating -log on the sample data.")
        # this check prevents division by 0 errors from the minus_log
        data[data == 0] = 1e-6
        # the operation is done in place
        tomopy.prep.normalize.minus_log(data, out=data)
        h.pstop("Finished calculating -log on the sample data.")

    return data