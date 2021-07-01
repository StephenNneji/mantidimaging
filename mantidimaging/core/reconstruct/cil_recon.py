# Copyright (C) 2021 ISIS Rutherford Appleton Laboratory UKRI
# SPDX - License - Identifier: GPL-3.0-or-later

from logging import getLogger
from typing import List

import numpy as np

# import cil
from cil.framework import AcquisitionGeometry, AcquisitionData, DataOrder

from cil.optimisation.algorithms import SIRT, CGLS, PDHG, GD
from cil.optimisation.operators import GradientOperator, BlockOperator
from cil.optimisation.functions import IndicatorBox, MixedL21Norm, \
                                       L2NormSquared, BlockFunction, \
                                       ZeroFunction, SmoothMixedL21Norm, \
                                       OperatorCompositionFunction

from cil.utilities.display import show2D

# CIL ASTRA plugin
from cil.plugins.astra.operators import  ProjectionOperator

# CIL Processors
from cil.processors import Slicer
from cil.processors import MaskGenerator
from cil.processors import Masker
from cil.processors import TransmissionAbsorptionConverter

# CIL IO
from cil.io import TIFFStackReader

import functools

from mantidimaging.core.data import Images
from mantidimaging.core.reconstruct.base_recon import BaseRecon
from mantidimaging.core.utility.data_containers import ProjectionAngles, ReconstructionParameters, ScalarCoR
from mantidimaging.core.utility.optional_imports import safe_import
from mantidimaging.core.utility.progress_reporting import Progress

LOG = getLogger(__name__)
tomopy = safe_import('tomopy')


def empty_array(shape):
    return (np.indices(shape).sum(axis=0) % 2).astype(np.float32)


class CILRecon(BaseRecon):

    @staticmethod
    def get_IMAT_AcquisitionGeometry(angles):
        pixel_num_h = 512
        pixel_num_v = 512
        pixel_size = (1.,1.)
        ag = AcquisitionGeometry.create_Parallel3D()\
              .set_panel([pixel_num_v, pixel_num_h], pixel_size=pixel_size)\
              .set_angles(angles=angles)
        return ag
    @staticmethod
    def set_up_TV_regularisation(image_geometry, acquisition_data):
        # Forward operator
        A2d = ProjectionOperator(image_geometry, acquisition_data.geometry, 'gpu')

        # Set up TV regularisation

        # Define Gradient Operator and BlockOperator 
        Grad = GradientOperator(image_geometry)
        K = BlockOperator(Grad,A2d)

        # Define BlockFunction F using the MixedL21Norm() and the L2NormSquared()
        # alpha = 1.0
        # f1 =  alpha * MixedL21Norm()
        f1 = MixedL21Norm()
        # f2 = 0.5 * L2NormSquared(b=ad2d)
        f2 = L2NormSquared(b=acquisition_data)
        # F = BlockFunction(f1,f2)

        # Define Function G simply as zero
        G = ZeroFunction()
        return (K, f1, f2, G)

    @staticmethod
    def find_cor(images: Images, slice_idx: int, start_cor: float, recon_params: ReconstructionParameters) -> float:
        return tomopy.find_center(images.sinograms,
                                  images.projection_angles(recon_params.max_projection_angle).value,
                                  ind=slice_idx,
                                  init=start_cor,
                                  sinogram_order=True)

    @staticmethod
    def single_sino(sino: np.ndarray, cor: ScalarCoR, proj_angles: ProjectionAngles,
                    recon_params: ReconstructionParameters):
        """
        Reconstruct a single slice from a single sinogram. Used for the preview and the single slice button.
        Should return a numpy array,
        """
        sino = BaseRecon.sino_recon_prep(sino)
        # volume = tomopy.recon(tomo=[sino],
        #                      sinogram_order=True,
        #                      theta=proj_angles.value,
        #                      center=cor.value,
        #                      algorithm=recon_params.algorithm,
        #                      filter_name=recon_params.filter_name)

        print("cor", cor)
        print("sino.shape", sino.shape)
        print("proj_angles", proj_angles.value[:10], "...")
        print("recon_params", recon_params)
        width = sino.shape[1]

        ag3D = CILRecon.get_IMAT_AcquisitionGeometry(proj_angles.value)
        # get a slice 
        ag = ag3D.get_centre_slice()
        ag.set_labels(DataOrder.ASTRA_AG_LABELS)
        # stick it into an AcquisitionData
        data = ag.allocate(None)
        data.fill(sino)
        
        ig = ag.get_ImageGeometry()
        # set up TV regularisation
        K, f1, f2, G = CILRecon.set_up_TV_regularisation(ig, data)

        # alpha = 1.0
        # f1 =  alpha * MixedL21Norm()
        # f2 = 0.5 * L2NormSquared(b=ad2d)
        F = BlockFunction( alpha * f1, 0.5 * f2)
        normK =  K.norm()
        sigma = 1
        tau = 1/(sigma*normK**2)

        pdhg = PDHG(f=F, g=G, operator=K, tau=tau, sigma=sigma, 
            max_iteration=100000, update_objective_interval=10)

        pdhg.run(num_iter, verbose=0, callback=None)
        return pdhg.solution.as_array()
        # slice = empty_array([width, width])
        # return slice

    @staticmethod
    def full(images: Images, cors: List[ScalarCoR], recon_params: ReconstructionParameters, progress=None):
        """
        Performs a volume reconstruction using sample data provided as sinograms.

        :param images: Array of sinogram images
        :param cors: Array of centre of rotation values
        :param proj_angles: Array of projection angles in radians
        :param recon_params: Reconstruction Parameters
        :param progress: Optional progress reporter
        :return: 3D image data for reconstructed volume
        """
        progress = Progress.ensure_instance(progress, task_name='CIL reconstruction')

        import multiprocessing
        ncores = multiprocessing.cpu_count()

        kwargs = {
            'ncore': ncores,
            'tomo': images.data,
            'sinogram_order': images._is_sinograms,
            'theta': images.projection_angles(recon_params.max_projection_angle).value,
            'center': [cor.value for cor in cors],
            'alpha': recon_params.alpha,
            'num_iter': recon_params.num_iter,
        }
        print("kwargs", kwargs)
        ag = CILRecon.get_IMAT_AcquisitionGeometry(
            images.projection_angles(recon_params.max_projection_angle).value
            )
        ag.set_labels(DataOrder.ASTRA_AG_LABELS)
        # stick it into an AcquisitionData
        data = ag.allocate(None)
        data.fill(images.data)
        
        ig = ag.get_ImageGeometry()
        # set up TV regularisation
        K, f1, f2, G = CILRecon.set_up_TV_regularisation(ig, data)

        # alpha = 1.0
        # f1 =  alpha * MixedL21Norm()
        # f2 = 0.5 * L2NormSquared(b=ad2d)
        F = BlockFunction( alpha * f1, 0.5 * f2)
        normK =  K.norm()
        sigma = 1
        tau = 1/(sigma*normK**2)

        algo = PDHG(f=F, g=G, operator=K, tau=tau, sigma=sigma, 
            max_iteration=100000, update_objective_interval=10)

        def myprogress(p, iter, obj, solution):
            p.update(steps=1, msg='', force_continue=False)
        with progress:
            # volume = tomopy.recon(**kwargs)
            prg = functools.partial(myprogress, progress)
            pdhg.run(num_iter, verbose=0, callback=prg)
        
            # width = images.width
            # slices = images.height
            # volume = empty_array([slices, width, width])

            LOG.info('Reconstructed 3D volume with shape: {0}'.format(volume.shape))
        return Images(algo.solution.as_array())
        


def allowed_recon_kwargs() -> dict:
    return {'CIL': ['alpha', 'num_iter']}
