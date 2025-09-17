#!/usr/bin/env python
#
# test_decaps.py
# Test query code for the Green, Schlafly, Finkbeiner et al. (2015) dust map.
#
# Copyright (C) 2025 Catherine Zucker, Gregory M. Green
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from __future__ import print_function, division

import unittest

import numpy as np
import astropy.coordinates as coords
import astropy.units as units
import os
import re
import time
import pickle

from .. import decaps
from ..std_paths import *


def parse_decaps_output(fname):
    with open(fname, "rb") as f:
        output = pickle.load(f)
        
    return output


class TestDECaPS(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        print('Loading DECaPS query object ...')
        t0 = time.time()

        fname = os.path.join(test_dir, 'decaps_test_data.pkl')
        self._test_data = parse_decaps_output(fname)

        # Set up DECaPS query object
        self._decaps = decaps.DECaPSQueryLite()


    def _get_equ(self, d, dist=None):
        """
        Get Equatorial (ICRS) coordinates of test data point.
        """
        return coords.SkyCoord(
            d['ra']*units.deg,
            d['dec']*units.deg,
            distance=dist,
            frame='icrs'
        )

    def _get_gal(self, d, dist=None):
        """
        Get Galactic coordinates of test data point.
        """
        return coords.SkyCoord(
            d['l']*units.deg,
            d['b']*units.deg,
            distance=dist,
            frame='galactic'
        )


    def test_equ_mean_far_scalar(self):
        """
        Test that mean reddening is correct in the far limit, using a single
        location on the sky at a time as input.
        """
        for d in self._test_data:
            c = self._get_gal(d, dist=1.e3*units.kpc)
            ebv_data = (d['mean'][-1])
            ebv_calc = self._decaps.query(c, mode='mean')
            np.testing.assert_allclose(ebv_data, ebv_calc, atol=0.001, rtol=0.0001)

    def test_equ_mean_far_vector(self):
        """
        Test that mean reddening is correct in the far limit, using a vector
        of coordinates as input.
        """
        l = [d['l']*units.deg for d in self._test_data]
        b = [d['b']*units.deg for d in self._test_data]
        dist = [1.e3*units.kpc for bb in b]
        c = coords.SkyCoord(l, b, distance=dist, frame='galactic')

        ebv_data = np.array([(d['mean'][-1]) for d in self._test_data])
        ebv_calc = self._decaps.query(c, mode='mean')

        np.testing.assert_allclose(ebv_data, ebv_calc, atol=0.001, rtol=0.0001)


    def test_equ_random_sample_vector(self):
        """
        Test that random sample of reddening at arbitary distance is actually
        from the set of possible reddening samples at that distance. Uses vector
        of coordinates/distances as input.
        """

        # Prepare coordinates (with random distances)
        l = [d['l']*units.deg for d in self._test_data]
        b = [d['b']*units.deg for d in self._test_data]
        dm = 3. + (25.-3.)*np.random.random(len(self._test_data))

        dist = [d*units.kpc for d in 10.**(dm/5.-2.)]
        dist_unitless = [d for d in 10.**(dm/5.-2.)]
        c = coords.SkyCoord(l, b, distance=dist, frame='galactic')

        ebv_data = np.array([
            self._interp_ebv(datum, d)
            for datum,d in zip(self._test_data, dist_unitless)
        ])
        ebv_calc = self._decaps.query(c, mode='random_sample')

        d_ebv = np.min(np.abs(ebv_data[:,:] - ebv_calc[:,None]), axis=1)


        np.testing.assert_allclose(d_ebv, 0., atol=0.001, rtol=0.0001)

    def test_equ_samples_vector(self):
        """
        Test that full set of samples of reddening at arbitary distance is
        correct. Uses vector of coordinates/distances as input.
        """

        # Prepare coordinates (with random distances)
        l = [d['l']*units.deg for d in self._test_data]
        b = [d['b']*units.deg for d in self._test_data]
        dm = 3. + (25.-3.)*np.random.random(len(self._test_data))

        dist = [d*units.kpc for d in 10.**(dm/5.-2.)]
        dist_unitless = [d for d in 10.**(dm/5.-2.)]
        c = coords.SkyCoord(l, b, distance=dist, frame='galactic')

        ebv_data = np.array([
            self._interp_ebv(datum, d)
            for datum,d in zip(self._test_data, dist_unitless)
        ])
        ebv_calc = self._decaps.query(c, mode='samples')

        np.testing.assert_allclose(ebv_data, ebv_calc, atol=0.001, rtol=0.0001)

    def test_equ_samples_scalar(self):
        """
        Test that full set of samples of reddening at arbitary distance is
        correct. Uses single set of coordinates/distance as input.
        """
        for d in self._test_data:
            # Prepare coordinates (with random distances)
            l = d['l']*units.deg
            b = d['b']*units.deg
            dm = 3. + (25.-3.)*np.random.random()

            dist = 10.**(dm/5.-2.)
            c = coords.SkyCoord(l, b, distance=dist*units.kpc, frame='galactic')

            ebv_data = self._interp_ebv(d, dist)
            ebv_calc = self._decaps.query(c, mode='samples')

            np.testing.assert_allclose(ebv_data, ebv_calc, atol=0.001, rtol=0.0001)

    def test_equ_random_sample_scalar(self):
        """
        Test that random sample of reddening at arbitary distance is actually
        from the set of possible reddening samples at that distance. Uses vector
        of coordinates/distances as input. Uses single set of
        coordinates/distance as input.
        """
        for d in self._test_data:
            # Prepare coordinates (with random distances)
            l = d['l']*units.deg
            b = d['b']*units.deg
            dm = 3. + (25.-3.)*np.random.random()

            dist = 10.**(dm/5.-2.)
            c = coords.SkyCoord(l, b, distance=dist*units.kpc, frame='galactic')

            ebv_data = self._interp_ebv(d, dist)
            ebv_calc = self._decaps.query(c, mode='random_sample')

            d_ebv = np.min(np.abs(ebv_data[:] - ebv_calc))

            np.testing.assert_allclose(d_ebv, 0., atol=0.001, rtol=0.0001)

    def test_equ_samples_nodist_vector(self):
        """
        Test that full set of samples of reddening vs. distance curves is
        correct. Uses vector of coordinates as input.
        """

        # Prepare coordinates
        l = [d['l']*units.deg for d in self._test_data]
        b = [d['b']*units.deg for d in self._test_data]

        c = coords.SkyCoord(l, b, frame='galactic')

        ebv_data = np.array([d['samples'] for d in self._test_data])
        ebv_calc = self._decaps.query(c, mode='samples')


        np.testing.assert_allclose(ebv_data, ebv_calc, atol=0.001, rtol=0.0001)

    def test_equ_random_sample_nodist_vector(self):
        """
        Test that a random sample of the reddening vs. distance curve is drawn
        from the full set of samples. Uses vector of coordinates as input.
        """

        # Prepare coordinates
        l = [d['l']*units.deg for d in self._test_data]
        b = [d['b']*units.deg for d in self._test_data]

        c = coords.SkyCoord(l, b, frame='galactic')

        ebv_data = np.array([d['samples'] for d in self._test_data])
        ebv_calc = self._decaps.query(c, mode='random_sample')
        
        d_ebv = np.min(np.abs(ebv_data[:,:,:] - ebv_calc[:,None,:]), axis=1)
        np.testing.assert_allclose(d_ebv, 0., atol=0.001, rtol=0.0001)

    def test_shape(self):
        """
        Test that the output shapes are as expected with input coordinate arrays
        of different shapes.
        """

        for mode in ['random_sample', 'median', 'mean', 'samples']:
            for reps in range(5):
                # Draw random coordinates, with different shapes
                n_dim = np.random.randint(1,4)
                shape = np.random.randint(1,7, size=(n_dim,))

                ra = -180. + 360.*np.random.random(shape)
                dec = -90. + 180. * np.random.random(shape)
                c = coords.SkyCoord(ra, dec, frame='icrs', unit='deg')

                ebv_calc = self._decaps.query(c, mode=mode)

                np.testing.assert_equal(ebv_calc.shape[:n_dim], shape)

                if mode == 'samples':
                    self.assertEqual(len(ebv_calc.shape), n_dim+2) # sample, distance
                else:
                    self.assertEqual(len(ebv_calc.shape), n_dim+1) # distance

    def _interp_ebv(self, datum, dist):
        """
        Calculate samples of E(B-V) at an arbitrary distance (in kpc) for one
        test coordinate.
        """
        dm = 5. * (np.log10(dist) + 2.)
        idx_ceil = np.searchsorted(datum['DM_bin_edges'], dm)
        if idx_ceil == 0:
            dist_0 = 10.**(datum['DM_bin_edges'][0]/5. - 2.)
            return dist/dist_0 * datum['samples'][:,0]
        elif idx_ceil == len(datum['DM_bin_edges']):
            return datum['samples'][:,-1]
        else:
            dm_ceil = datum['DM_bin_edges'][idx_ceil]
            dm_floor = datum['DM_bin_edges'][idx_ceil-1]
            a = (dm_ceil - dm) / (dm_ceil - dm_floor)
            return (
                (1.-a) * datum['samples'][:,idx_ceil]
                +    a * datum['samples'][:,idx_ceil-1]
            )



if __name__ == '__main__':
    unittest.main()
