#!/usr/bin/env python3
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
import sys, os

sys.path.append(os.path.join('..', 'nvcl_kit'))
from nvcl_kit import NVCLKit

class TestNVCLKit(unittest.TestCase):
    def setup_param_obj(self):
        param_obj = SimpleNamespace()
        setattr(param_obj, "BBOX", {"west": -180.0,"south": -90.0,"east": 180.0,"north": 0.0})
        setattr(param_obj, "WFS_URL", "http://blah.blah.blah/nvcl/geoserver/wfs")
        setattr(param_obj, "BOREHOLE_CRS", "EPSG:4283")
        setattr(param_obj, "WFS_VERSION", "1.1.0")
        setattr(param_obj, "NVCL_URL", "https://blah.blah.blah/nvcl/NVCLDataServices")
        return param_obj

    @unittest.mock.patch('nvcl_kit.WebFeatureService', autospec=True)
    def test_empty_wfs(self, mock_wfs):
            wfs_obj = mock_wfs.return_value
            wfs_obj.getfeature.return_value = Mock()

            # Test empty but valid response
            with open('empty_wfs.txt') as fp:
                wfs_resp_str = fp.readline()
                wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str
                param_obj = self.setup_param_obj()
                kit = NVCLKit(param_obj)
                l = kit.get_boreholes_list(20)
                self.assertEqual(l, [])

    @unittest.mock.patch('nvcl_kit.WebFeatureService', autospec=True)
    def test_full_wfs(self, mock_wfs):
            wfs_obj = mock_wfs.return_value
            wfs_obj.getfeature.return_value = Mock()

            # Test full response, maximum number of boreholes is enforced
            with open('full_wfs3.txt') as fp:
                wfs_resp_list = fp.readlines()
                wfs_resp_str = ''.join(wfs_resp_list)
                wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str.rstrip('\n')
                param_obj = self.setup_param_obj()
                kit = NVCLKit(param_obj)
                l = kit.get_boreholes_list(20)
                self.assertEqual(len(l), 20)


if __name__ == '__main__':
    unittest.main()
