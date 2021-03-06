#!/usr/bin/env pytest
# -*- coding: utf-8 -*-
###############################################################################
# $Id$
#
# Project:  GDAL/OGR Test Suite
# Purpose:  test librarified gdalbuildvrt
# Author:   Even Rouault <even dot rouault @ spatialys dot com>
#
###############################################################################
# Copyright (c) 2016, Even Rouault <even dot rouault @ spatialys dot com>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
###############################################################################

import struct

from osgeo import gdal

###############################################################################
# Simple test


def test_gdalbuildvrt_lib_1():

    # Source = String
    ds = gdal.BuildVRT('', '../gcore/data/byte.tif')
    assert ds is not None, 'got error/warning'

    assert ds.GetRasterBand(1).Checksum() == 4672, 'Bad checksum'

    # Source = Array of string
    ds = gdal.BuildVRT('', ['../gcore/data/byte.tif'])
    assert ds is not None, 'got error/warning'

    assert ds.GetRasterBand(1).Checksum() == 4672, 'Bad checksum'

    # Source = Dataset
    ds = gdal.BuildVRT('', gdal.Open('../gcore/data/byte.tif'))
    assert ds is not None, 'got error/warning'

    assert ds.GetRasterBand(1).Checksum() == 4672, 'Bad checksum'

    # Source = Array of dataset
    ds = gdal.BuildVRT('', [gdal.Open('../gcore/data/byte.tif')])
    assert ds is not None, 'got error/warning'

    assert ds.GetRasterBand(1).Checksum() == 4672, 'Bad checksum'

###############################################################################
# Test callback


def mycallback(pct, msg, user_data):
    # pylint: disable=unused-argument
    user_data[0] = pct
    return 1


def test_gdalbuildvrt_lib_2():

    tab = [0]
    ds = gdal.BuildVRT('', '../gcore/data/byte.tif', callback=mycallback, callback_data=tab)
    assert ds is not None

    assert ds.GetRasterBand(1).Checksum() == 4672, 'Bad checksum'

    assert tab[0] == 1.0, 'Bad percentage'

    ds = None


###############################################################################
# Test creating overviews


def test_gdalbuildvrt_lib_ovr():

    tmpfilename = '/vsimem/my.vrt'
    ds = gdal.BuildVRT(tmpfilename, '../gcore/data/byte.tif')
    ds.BuildOverviews('NEAR', [2])
    ds = None
    ds = gdal.Open(tmpfilename)
    assert ds.GetRasterBand(1).GetOverviewCount() == 1
    ds = None
    gdal.GetDriverByName('VRT').Delete(tmpfilename)



def test_gdalbuildvrt_lib_te_partial_overlap():

    ds = gdal.BuildVRT('', '../gcore/data/byte.tif', outputBounds=[440600, 3750060, 441860, 3751260], xRes=30, yRes=60)
    assert ds is not None

    assert ds.GetRasterBand(1).Checksum() == 8454
    xml = ds.GetMetadata('xml:VRT')[0]
    assert '<SrcRect xOff="0" yOff="1" xSize="19" ySize="19" />' in xml
    assert '<DstRect xOff="4" yOff="0" xSize="38" ySize="19" />' in xml


###############################################################################
# Test BuildVRT() with sources that can't be opened by name

def test_gdalbuildvrt_lib_mem_sources():

    def create_sources():
        src1_ds = gdal.GetDriverByName('MEM').Create('i_have_a_name_but_nobody_can_open_me_through_it', 1, 1)
        src1_ds.SetGeoTransform([2,1,0,49,0,-1])
        src1_ds.GetRasterBand(1).Fill(100)

        src2_ds = gdal.GetDriverByName('MEM').Create('', 1, 1)
        src2_ds.SetGeoTransform([3,1,0,49,0,-1])
        src2_ds.GetRasterBand(1).Fill(200)

        return src1_ds, src2_ds

    def scenario_1():
        src1_ds, src2_ds = create_sources()
        vrt_ds = gdal.BuildVRT('', [src1_ds, src2_ds])
        vals = struct.unpack('B' * 2, vrt_ds.ReadRaster())
        assert vals == (100, 200)

        vrt_of_vrt_ds = gdal.BuildVRT('', [vrt_ds])
        vals = struct.unpack('B' * 2, vrt_of_vrt_ds.ReadRaster())
        assert vals == (100, 200)

    # Alternate scenario where the Python objects of sources and intermediate
    # VRT are no longer alive when the VRT of VRT is accessed
    def scenario_2():
        def get_vrt_of_vrt():
            src1_ds, src2_ds = create_sources()
            return gdal.BuildVRT('', [ gdal.BuildVRT('', [src1_ds, src2_ds]) ])
        vrt_of_vrt_ds = get_vrt_of_vrt()
        vals = struct.unpack('B' * 2, vrt_of_vrt_ds.ReadRaster())
        assert vals == (100, 200)

    scenario_1()
    scenario_2()
