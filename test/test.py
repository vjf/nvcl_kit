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
        #
        # Test empty but valid WFS response
        #
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
        with open('empty_wfs.txt') as fp:
            wfs_resp_str = fp.readline()
            wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str
            param_obj = self.setup_param_obj(MAX_BOREHOLES)
            kit = NVCLKit(param_obj)
            l = kit.get_boreholes_list()
            self.assertEqual(l, [])


    @unittest.mock.patch('nvcl_kit.WebFeatureService', autospec=True)
    def test_max_bh_wfs(self, mock_wfs):
        #
        # Test full WFS response, maximum number of boreholes is enforced
        #
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
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
        #
        # Test full WFS response, unlimited number of boreholes
        #
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
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


    def setup_kit(self):
        kit = None
        with unittest.mock.patch('nvcl_kit.WebFeatureService') as mock_wfs:
            wfs_obj = mock_wfs.return_value
            wfs_obj.getfeature.return_value = Mock()
            with open('full_wfs3.txt') as fp:
                wfs_resp_list = fp.readlines()
                wfs_resp_str = ''.join(wfs_resp_list)
                wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str.rstrip('\n')
                param_obj = self.setup_param_obj(0)
                kit = NVCLKit(param_obj)
        return kit
   

    def test_imagelog_data(self):
        #
        # Test get_imagelog_data()
        #
        kit = self.setup_kit()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                resp_list = fp.readlines()
                resp_str = ''.join(resp_list)
                open_obj.__enter__.return_value.read.return_value = resp_str 
                imagelog_data_list = kit.get_imagelog_data("blah")
                self.assertEqual(len(imagelog_data_list), 5)
        

    def test_profilometer_data(self):
        #
        # Test get_profilometer_data()
        #
        kit = self.setup_kit()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                resp_list = fp.readlines()
                resp_str = ''.join(resp_list)
                open_obj.__enter__.return_value.read.return_value = resp_str 
                prof_data_list = kit.get_profilometer_data("blah")
                self.assertEqual(len(prof_data_list), 1)

        
    def test_spectrallog_data(self):
        #
        # Test get_spectrallog_data()
        #
        kit = self.setup_kit()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                resp_list = fp.readlines()
                resp_str = ''.join(resp_list)
                open_obj.__enter__.return_value.read.return_value = resp_str 
                spectral_data_list = kit.get_spectrallog_data("blah")
                self.assertEqual(len(spectral_data_list), 15)

    # get_borehole_data        
    # get_boreholes_list ?


if __name__ == '__main__':
    unittest.main()
