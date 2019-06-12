import os.path
import unittest
from collections import MutableMapping
from typing import TypeVar, Iterator, List

import xarray as xr

from xcube.api import new_cube
from xcube.util.dsio import rimraf

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')
_T_co = TypeVar('_T_co')
_VT_co = TypeVar('_VT_co')

CUBE_PATH = "cube.zarr"


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

    @classmethod
    def setUpClass(cls):
        rimraf(CUBE_PATH)
        cube = new_cube(variables=dict(precipitation=0.4, temperature=275.2, soil_moisture=0.5))
        cube.to_zarr(CUBE_PATH)

    @classmethod
    def tearDownClass(cls):
        rimraf(CUBE_PATH)

    def test_storage(self):
        store = MyStore(CUBE_PATH)
        ds = xr.open_zarr(store)
        self.assertIsNotNone(ds)
