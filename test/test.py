#!/usr/bin/env python3
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
import sys, os

sys.path.append(os.path.join('..', 'nvcl_kit'))
from nvcl_kit import NVCLKit

MAX_BOREHOLES = 20

class TestNVCLKit(unittest.TestCase):
    def setup_param_obj(self, max_boreholes):
        param_obj = SimpleNamespace()
        param_obj.BBOX = {"west": -180.0,"south": -90.0,"east": 180.0,"north": 0.0}
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.BOREHOLE_CRS = "EPSG:4283"
        param_obj.WFS_VERSION = "1.1.0"
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.MAX_BOREHOLES = max_boreholes
        return param_obj


    @unittest.mock.patch('nvcl_kit.WebFeatureService', autospec=True)
    def test_empty_wfs(self, mock_wfs):
            wfs_obj = mock_wfs.return_value
            wfs_obj.getfeature.return_value = Mock()

            # Test empty but valid response
            with open('empty_wfs.txt') as fp:
                wfs_resp_str = fp.readline()
                wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str
                param_obj = self.setup_param_obj(MAX_BOREHOLES)
                kit = NVCLKit(param_obj)
                l = kit.get_boreholes_list()
                self.assertEqual(l, [])


    @unittest.mock.patch('nvcl_kit.WebFeatureService', autospec=True)
    def test_max_bh_wfs(self, mock_wfs):
            wfs_obj = mock_wfs.return_value
            wfs_obj.getfeature.return_value = Mock()

            # Test full response, maximum number of boreholes is enforced
            with open('full_wfs3.txt') as fp:
                wfs_resp_list = fp.readlines()
                wfs_resp_str = ''.join(wfs_resp_list)
                wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str.rstrip('\n')
                param_obj = self.setup_param_obj(MAX_BOREHOLES)
                kit = NVCLKit(param_obj)
                l = kit.get_boreholes_list()
                self.assertEqual(len(l), MAX_BOREHOLES)
                l = kit.get_nvcl_id_list()
                self.assertEqual(len(l), MAX_BOREHOLES)


    @unittest.mock.patch('nvcl_kit.WebFeatureService', autospec=True)
    def test_all_bh_wfs(self, mock_wfs):
            wfs_obj = mock_wfs.return_value
            wfs_obj.getfeature.return_value = Mock()

            # Test full response, maximum number of boreholes is enforced
            with open('full_wfs3.txt') as fp:
                wfs_resp_list = fp.readlines()
                wfs_resp_str = ''.join(wfs_resp_list)
                wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str.rstrip('\n')
                param_obj = self.setup_param_obj(0)
                kit = NVCLKit(param_obj)
                l = kit.get_boreholes_list()
                self.assertEqual(len(l), 102)
                l = kit.get_nvcl_id_list()
                self.assertEqual(len(l), 102)
   

    @unittest.mock.patch('nvcl_kit.urllib', autospec=True)
    def test_imagelog_data(self, mock_urllib):
        request_obj = mock_urllib.return_value
        request_obj.request.return_value = Mock()
        request_obj.request.return_value.url_open.return_value = Mock()
        self.assertEqual(0,0)
        # TODO: Complete this
        #with open('dataset_coll.txt') as fp:
        #    ds_coll_resp_list = fp.readlines()
        #    ds_coll_resp_str = ''.join(wfs_resp_list)
        #    request_obj.request.return_value.url_open.return_value.read.return_value = ds_coll_resp_str 
        #    param_obj = self.setup_param_obj(0)
        #    kit = NVCLKit(param_obj)
        #    nvcl_list = kit.get_nvcl_id_list()
        #    image_data_list = kit.get_imagelog_data(nvcl_list[0])
        
    # TODO: Test receiving borehole data

if __name__ == '__main__':
    unittest.main()
