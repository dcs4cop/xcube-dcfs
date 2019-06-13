import os.path
import shutil
import unittest
import warnings
from collections import MutableMapping
from typing import TypeVar, Iterator, List

import numpy as np
import pandas as pd
import xarray as xr

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')
_T_co = TypeVar('_T_co')
_VT_co = TypeVar('_VT_co')


class MyStore(MutableMapping):

    def __init__(self, path):
        print(f'MyStore.init: {path}')
        self._path = path

    def __contains__(self, k: _KT) -> bool:
        print(f'MyStore.contains: {k}')
        path = os.path.join(self._path, k)
        return os.path.exists(path)

    def __setitem__(self, k: _KT, v: _VT) -> None:
        print(f'MyStore.set: {k} = {v}')
        pass

    def __delitem__(self, k: _KT) -> None:
        print(f'MyStore.del: {k}')
        pass

    def __getitem__(self, k: _KT) -> _VT_co:
        print(f'MyStore.get: {k}')
        path = os.path.join(self._path, k)
        with open(path, 'rb') as fp:
            return fp.read()

    def __len__(self) -> int:
        print(f'MyStore.len')
        return len(self.listdir(''))

    def __iter__(self) -> Iterator[_T_co]:
        print(f'MyStore.iter')
        return iter(self.listdir(''))

    def listdir(self, path: str) -> List[str]:
        print(f'MyStore.listdir: {path}')
        dir_path = os.path.join(self._path, path)
        return os.listdir(dir_path)


class ZarrTest(unittest.TestCase):
    CUBE_PATH = "cube.zarr"

    @classmethod
    def setUpClass(cls):
        rimraf(cls.CUBE_PATH)
        cube = new_cube(variables=dict(precipitation=0.4, temperature=275.2, soil_moisture=0.5))
        cube.to_zarr(cls.CUBE_PATH)

    @classmethod
    def tearDownClass(cls):
        rimraf(cls.CUBE_PATH)

    def test_storage(self):
        store = MyStore(self.CUBE_PATH)
        ds = xr.open_zarr(store)
        self.assertIsNotNone(ds)


_TIME_DTYPE = "datetime64[s]"
_TIME_UNITS = "seconds since 1970-01-01T00:00:00"
_TIME_CALENDAR = "proleptic_gregorian"


def new_cube(title="Test Cube",
             width=360,
             height=180,
             spatial_res=1.0,
             lon_start=-180.0,
             lat_start=-90.0,
             time_periods=5,
             time_freq="D",
             time_start='2010-01-01T00:00:00',
             drop_bounds=False,
             variables=None):
    """
    Create a new empty cube. Useful for testing.

    :param title: A title.
    :param width: Horizontal number of grid cells
    :param height: Vertical number of grid cells
    :param spatial_res: Spatial resolution in degrees
    :param lon_start: Minimum longitude value
    :param lat_start: Minimum latitude value
    :param time_periods: Number of time steps
    :param time_freq: Duration of each time step
    :param time_start: First time value
    :param drop_bounds: If True, coordinate bounds variables are not created.
    :param variables: Dictionary of data variables to be added.
    :return: A cube instance
    """
    lon_end = lon_start + width * spatial_res
    lat_end = lat_start + height * spatial_res
    if width < 0 or height < 0 or spatial_res <= 0.0:
        raise ValueError()
    if lon_start < -180. or lon_end > 180. or lat_start < -90. or lat_end > 90.:
        raise ValueError()
    if time_periods < 0:
        raise ValueError()

    lon_data = np.linspace(lon_start + 0.5 * spatial_res, lon_end - 0.5 * spatial_res, width)
    lon = xr.DataArray(lon_data, dims="lon")
    lon.attrs["units"] = "degrees_east"

    lat_data = np.linspace(lat_start + 0.5 * spatial_res, lat_end - 0.5 * spatial_res, height)
    lat = xr.DataArray(lat_data, dims="lat")
    lat.attrs["units"] = "degrees_north"

    time_data_2 = pd.date_range(start=time_start, periods=time_periods + 1, freq=time_freq).values
    time_data_2 = time_data_2.astype(dtype=_TIME_DTYPE)
    time_delta = time_data_2[1] - time_data_2[0]
    time_data = time_data_2[0:-1] + time_delta // 2
    time = xr.DataArray(time_data, dims="time")
    time.encoding["units"] = _TIME_UNITS
    time.encoding["calendar"] = _TIME_CALENDAR

    time_data_2 = pd.date_range(time_start, periods=time_periods + 1, freq=time_freq)

    coords = dict(lon=lon, lat=lat, time=time)
    if not drop_bounds:
        lon_bnds_data = np.zeros((width, 2), dtype=np.float64)
        lon_bnds_data[:, 0] = np.linspace(lon_start, lon_end - spatial_res, width)
        lon_bnds_data[:, 1] = np.linspace(lon_start + spatial_res, lon_end, width)
        lon_bnds = xr.DataArray(lon_bnds_data, dims=("lon", "bnds"))
        lon_bnds.attrs["units"] = "degrees_east"

        lat_bnds_data = np.zeros((height, 2), dtype=np.float64)
        lat_bnds_data[:, 0] = np.linspace(lat_start, lat_end - spatial_res, height)
        lat_bnds_data[:, 1] = np.linspace(lat_start + spatial_res, lat_end, height)
        lat_bnds = xr.DataArray(lat_bnds_data, dims=("lat", "bnds"))
        lat_bnds.attrs["units"] = "degrees_north"

        time_bnds_data = np.zeros((time_periods, 2), dtype="datetime64[ns]")
        time_bnds_data[:, 0] = time_data_2[:-1]
        time_bnds_data[:, 1] = time_data_2[1:]
        time_bnds = xr.DataArray(time_bnds_data, dims=("time", "bnds"))
        time_bnds.encoding["units"] = _TIME_UNITS
        time_bnds.encoding["calendar"] = _TIME_CALENDAR

        lon.attrs["bounds"] = "lon_bnds"
        lat.attrs["bounds"] = "lat_bnds"
        time.attrs["bounds"] = "time_bnds"

        coords.update(dict(lon_bnds=lon_bnds, lat_bnds=lat_bnds, time_bnds=time_bnds))

    attrs = {
        "Conventions": "CF-1.7",
        "title": title,
        "time_coverage_start": str(time_data_2[0]),
        "time_coverage_end": str(time_data_2[-1]),
        "geospatial_lon_min": lon_start,
        "geospatial_lon_max": lon_end,
        "geospatial_lon_units": "degrees_east",
        "geospatial_lat_min": lat_start,
        "geospatial_lat_max": lat_end,
        "geospatial_lat_units": "degrees_north",
    }

    # TODO (forman): allow variable values to be expressions so values will be computed from coords using numexpr

    data_vars = {}
    if variables:
        dims = ("time", "lat", "lon")
        shape = (time_periods, height, width)
        size = time_periods * height * width
        for var_name, data in variables.items():
            if isinstance(data, xr.DataArray):
                data_vars[var_name] = data
            elif isinstance(data, int) or isinstance(data, float) or isinstance(data, bool):
                data_vars[var_name] = xr.DataArray(np.full(shape, data), dims=dims)
            elif data is None:
                data_vars[var_name] = xr.DataArray(np.random.uniform(0.0, 1.0, size).reshape(shape), dims=dims)
            else:
                data_vars[var_name] = xr.DataArray(data, dims=dims)

    return xr.Dataset(data_vars=data_vars, coords=coords, attrs=attrs)


def rimraf(path):
    """
    The UNIX command `rm -rf`.
    Recursively remove directory or single file.

    :param path:  directory or single file
    """
    if os.path.isdir(path):
        try:
            shutil.rmtree(path, ignore_errors=False)
        except OSError:
            warnings.warn(f"failed to remove file {path}")
    elif os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            warnings.warn(f"failed to remove file {path}")
            pass
