#!/usr/bin/env python3
import sys, os
import unittest
from unittest.mock import patch, Mock
from requests.exceptions import Timeout, RequestException
from owslib.util import ServiceException
from http.client import HTTPException
import logging

from types import SimpleNamespace

from nvcl_kit.reader import NVCLReader

MAX_BOREHOLES = 20

class TestNVCLReader(unittest.TestCase):


    def setup_param_obj(self, max_boreholes=None, bbox=None):
        ''' Create a parameter object for passing to NVCLReader constructor
 
        :param max_boreholes: maximum number of boreholes to download
        :returns: SimpleNamespace() object containing parameters
        '''
        param_obj = SimpleNamespace()
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        if bbox:
            param_obj.BBOX = bbox
        if max_boreholes:
            param_obj.MAX_BOREHOLES = max_boreholes
        return param_obj


    @unittest.mock.patch('nvcl_kit.reader.WebFeatureService', autospec=True)
    def test_logging_level(self, mock_wfs):
        ''' Test the 'log_lvl' parameter in the constructor
        '''
        # Use an empty response
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
        with open('empty_wfs.txt') as fp:
            wfs_obj.getfeature.return_value.read.return_value = fp.readline()
            with self.assertLogs('nvcl_kit.reader', level='DEBUG') as nvcl_log:
                param_obj = SimpleNamespace()
                param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
                param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
                rdr = NVCLReader(param_obj, log_lvl=logging.DEBUG)
                self.assertIn("_fetch_boreholes_list(0)", nvcl_log.output[0])


    def try_input_param(self, param_obj, msg):
        ''' Used to test variations in erroneous constructor input parameters
            :param param_obj: input parameter object
            :param msg: warning messge produced
        '''
        with self.assertLogs('nvcl_kit.reader', level='WARN') as nvcl_log:
            rdr = NVCLReader(param_obj)
            self.assertIn(msg, nvcl_log.output[0])
            self.assertEqual(rdr.wfs, None)


    def test_bad_constr_param(self):
        ''' Tests that if it has bad 'param_obj' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        self.try_input_param({'ffgf':43},
                              "'param_obj' is not a SimpleNamespace() object")


    def test_bad_crs_param(self):
        ''' Tests that if has a bad 'BOREHOLE_CRS' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.BOREHOLE_CRS = "blah"
        self.try_input_param(param_obj, "'BOREHOLE_CRS' parameter is not an EPSG string")


    def test_bad_wfs_ver_param1(self):
        ''' Tests that if has a bad 'WFS_VERSION' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.WFS_VERSION = 1.1
        self.try_input_param(param_obj, "'WFS_VERSION' parameter is not a numeric string")


    def test_bad_wfs_ver_param2(self):
        ''' Tests that if has a badly formatted 'WFS_VERSION' parameter it
            issues a warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.WFS_VERSION = "v1.1"
        self.try_input_param(param_obj, "'WFS_VERSION' parameter is not a numeric string")


    def test_bad_maxbh_param(self):
        ''' Tests that if has a bad 'MAX_BOREHOLES' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.MAX_BOREHOLES = "blah"
        self.try_input_param(param_obj, "'MAX_BOREHOLES' parameter is not an integer")


    def test_bad_bbox_param1(self):
        ''' Tests that if has a bad 'BBOX' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.BBOX = "blah"
        self.try_input_param(param_obj, "'BBOX' parameter is not a dict")


    def test_bad_bbox_param2(self):
        ''' Tests that if it is missing part of 'BBOX' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.BBOX = { 'north': 0, 'west':90, 'east':180 }
        self.try_input_param(param_obj, "BBOX['south'] parameter is missing")


    def test_bad_bbox_param3(self):
        ''' Tests that if part of 'BBOX' parameter is not a number it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.BBOX = { 'south': '-40', 'north': 0, 'west': 90, 'east':180 }
        self.try_input_param(param_obj, "BBOX['south'] parameter is not a number")


    def test_missing_wfs_param(self):
        ''' Tests that if it is missing 'WFS_URL' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        self.try_input_param(param_obj, "'WFS_URL' parameter is missing")


    def test_bad_wfs_param(self):
        ''' Tests that if it has a bad 'WFS_URL' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.WFS_URL = None
        self.try_input_param(param_obj, "'WFS_URL' parameter is not a string")


    def test_missing_nvcl_param(self):
        ''' Tests that if it is missing 'NVCL_URL' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        self.try_input_param(param_obj, "'NVCL_URL' parameter is missing")


    def test_bad_nvcl_param(self):
        ''' Tests that if it has a bad 'NVCL_URL' parameter it issues a
            warning message and returns wfs attribute as None
        '''
        param_obj = SimpleNamespace()
        param_obj.NVCL_URL = None
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        self.try_input_param(param_obj, "'NVCL_URL' parameter is not a string")


    def wfs_exception_tester(self, mock_wfs, excep, msg):
        ''' Creates an exception in owslib getfeature() read()
            and tests to see that the correct warning message is generated

        :param mock_wfs: mock version of WebFeatureService() object
        :param excep: exception that is to be created
        :param msg: warning message to test for
        '''
        mock_wfs.side_effect = excep
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
        wfs_obj.getfeature.return_value.read.side_effect = excep
        with self.assertLogs('nvcl_kit.reader', level='WARN') as nvcl_log:
            param_obj = self.setup_param_obj(max_boreholes=MAX_BOREHOLES)
            rdr = NVCLReader(param_obj)
            self.assertIn(msg, nvcl_log.output[0])
            self.assertEqual(rdr.wfs, None)


    @unittest.mock.patch('nvcl_kit.reader.WebFeatureService', autospec=True)
    def test_exception_wfs(self, mock_wfs):
        ''' Tests that NVCLReader() can handle exceptions in WebFeatureService
            function
        '''
        self.wfs_exception_tester(mock_wfs, ServiceException, 'WFS error:')
        self.wfs_exception_tester(mock_wfs, RequestException, 'Request error:')
        self.wfs_exception_tester(mock_wfs, HTTPException, 'HTTP error code returned:')
        self.wfs_exception_tester(mock_wfs, OSError, 'OS Error:')


    def wfs_read_exception_tester(self, mock_wfs, excep, msg):
        ''' Creates an exception in owslib getfeature() and tests for the
            correct warning message
        :param mock_wfs: mock version of WebFeatureService() object
        :param excep: exception that is to be created
        :param msg: warning message to test for
        '''
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
        wfs_obj.getfeature.return_value.read.side_effect = excep
        with self.assertLogs('nvcl_kit.reader', level='WARN') as nvcl_log:
            param_obj = self.setup_param_obj(max_boreholes=MAX_BOREHOLES)
            rdr = NVCLReader(param_obj)
            l = rdr.get_boreholes_list()
            self.assertIn(msg, nvcl_log.output[0])
            self.assertEqual(rdr.wfs, None)


    @unittest.mock.patch('nvcl_kit.reader.WebFeatureService', autospec=True)
    def test_exception_getfeature_read(self, mock_wfs):
        ''' Tests that can handle exceptions in getfeature's read() function
        '''
        for excep in [Timeout, RequestException, HTTPException, ServiceException, OSError]:
            self.wfs_read_exception_tester(mock_wfs, excep, 'WFS GetFeature failed')


    @unittest.mock.patch('nvcl_kit.reader.WebFeatureService', autospec=True)
    def test_empty_wfs(self, mock_wfs):
        ''' Test empty but valid WFS response
            (tests get_boreholes_list() & get_nvcl_id_list() )
        '''
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
        with open('empty_wfs.txt') as fp:
            wfs_obj.getfeature.return_value.read.return_value = fp.readline()
            param_obj = self.setup_param_obj(max_boreholes=MAX_BOREHOLES)
            rdr = NVCLReader(param_obj)
            l = rdr.get_boreholes_list()
            self.assertEqual(l, [])
            l = rdr.get_nvcl_id_list()
            self.assertEqual(l, [])
            wfs_obj.getfeature.return_value.read.assert_called_once()


    @unittest.mock.patch('nvcl_kit.reader.WebFeatureService', autospec=True)
    def test_max_bh_wfs(self, mock_wfs):
        ''' Test full WFS response, maximum number of boreholes is enforced
            (tests get_boreholes_list() & get_nvcl_id_list() )
        '''
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
        with open('full_wfs3.txt') as fp:
            wfs_obj.getfeature.return_value.read.return_value = fp.read().rstrip('\n')
            param_obj = self.setup_param_obj(max_boreholes=MAX_BOREHOLES)
            rdr = NVCLReader(param_obj)
            l = rdr.get_boreholes_list()
            self.assertEqual(len(l), MAX_BOREHOLES)
            l = rdr.get_nvcl_id_list()
            self.assertEqual(len(l), MAX_BOREHOLES)


    @unittest.mock.patch('nvcl_kit.reader.WebFeatureService', autospec=True)
    def test_all_bh_wfs(self, mock_wfs):
        ''' Test full WFS response, unlimited number of boreholes
            (tests get_boreholes_list() & get_nvcl_id_list() )
        '''
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
        with open('full_wfs3.txt') as fp:
            wfs_obj.getfeature.return_value.read.return_value = fp.read().rstrip('\n')
            param_obj = self.setup_param_obj()
            rdr = NVCLReader(param_obj)
            l = rdr.get_boreholes_list()
            self.assertEqual(len(l), 102)
            # Test with all fields having values
            self.assertEqual(l[4], {
                'nvcl_id': '12991',
                'x': 145.67616489, 'y': -41.61921239,
                'href': 'http://www.blah.gov.au/resource/feature/blah/borehole/12991',
                'name': 'MC3',
                'description': 'descr',
                'purpose': 'purp',
                'status': 'STATUS',
                'drillingMethod': 'unknown',
                'operator': 'Opera',
                'driller': 'Blah Exploration Pty Ltd',
                'drillStartDate': '1978-05-28Z',
                'drillEndDate': '1979-05-28Z',
                'startPoint': 'unknown',
                'inclinationType': 'inclined down',
                'boreholeMaterialCustodian': 'blah',
                'boreholeLength_m': '60.3',
                'elevation_m': '791.4',
                'elevation_srs': 'http://www.opengis.net/def/crs/EPSG/0/5711',
                'positionalAccuracy': '1.2',
                'source': 'Src',
                'parentBorehole_uri': 'http://blah.org/blah-d354454546e3esd3454',
                'metadata_uri': 'http://blah.org/geosciml-drillhole-locations-in-blah-d354a70a4a29536166ab8a9ca6470a79d628c05e',
                'genericSymbolizer': 'SSSSS',
                'z': 791.4})

            # Test an almost completely empty borehole
            self.assertEqual(l[5], {'nvcl_id': '12992', 'x': 145.67585285, 'y': -41.61422342, 'href': '', 'name': '', 'description': '', 'purpose': '', 'status': '', 'drillingMethod': '', 'operator': '', 'driller': '', 'drillStartDate': '', 'drillEndDate': '', 'startPoint': '', 'inclinationType': '', 'boreholeMaterialCustodian': '', 'boreholeLength_m': '', 'elevation_m': '', 'elevation_srs': '', 'positionalAccuracy': '', 'source': '', 'parentBorehole_uri': '', 'metadata_uri': '', 'genericSymbolizer': '', 'z': 0.0})

            l = rdr.get_nvcl_id_list()
            self.assertEqual(len(l), 102)
            self.assertEqual(l[0:3], ['10026','10027','10343'])


    @unittest.mock.patch('nvcl_kit.reader.WebFeatureService', autospec=True)
    def test_bbox_wfs(self, mock_wfs):
        ''' Test bounding box precision of selecting boreholes
            There are two boreholes in the test data: one is just within
            the bounding box, the other is just outside
        '''
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
        with open('bbox_wfs.txt') as fp:
            wfs_obj.getfeature.return_value.read.return_value = fp.read().rstrip('\n')
            param_obj = self.setup_param_obj(max_boreholes=0, bbox={"west": 146.0,"south": -41.2,"east": 147.2,"north": -40.5})
            rdr = NVCLReader(param_obj)
            l = rdr.get_boreholes_list()
            self.assertEqual(len(l), 1)
            l = rdr.get_nvcl_id_list()
            self.assertEqual(len(l), 1)


    @unittest.mock.patch('nvcl_kit.reader.WebFeatureService', autospec=True)
    def test_bad_coord_wfs(self, mock_wfs):
        ''' Test WFS response with bad coordinates
            (tests get_boreholes_list() & get_nvcl_id_list() )
        '''
        wfs_obj = mock_wfs.return_value
        wfs_obj.getfeature.return_value = Mock()
        with open('badcoord_wfs.txt') as fp:
            wfs_obj.getfeature.return_value.read.return_value = fp.read().rstrip('\n')
            param_obj = self.setup_param_obj()
            with self.assertLogs('nvcl_kit.reader', level='WARN') as nvcl_log:
                rdr = NVCLReader(param_obj)
                self.assertIn('Cannot parse collar coordinates', nvcl_log.output[0])


    def setup_reader(self):
        ''' Initialises NVCLReader() object

        :returns: NVLKit() object
        '''
        rdr = None
        with unittest.mock.patch('nvcl_kit.reader.WebFeatureService') as mock_wfs:
            wfs_obj = mock_wfs.return_value
            wfs_obj.getfeature.return_value = Mock()
            with open('full_wfs3.txt') as fp:
                wfs_obj.getfeature.return_value.read.return_value = fp.read().rstrip('\n')
                param_obj = self.setup_param_obj()
                rdr = NVCLReader(param_obj)
        return rdr 
   

    def test_imagelog_data(self):
        ''' Test get_imagelog_data()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                imagelog_data_list = rdr.get_imagelog_data("blah")
                self.assertEqual(len(imagelog_data_list), 5)

                self.assertEqual(imagelog_data_list[0].log_id, '2023a603-7b31-4c97-ad59-efb220d93d9')
                self.assertEqual(imagelog_data_list[0].log_name, 'Tray')
                self.assertEqual(imagelog_data_list[0].log_type, '1')
                self.assertEqual(imagelog_data_list[0].algorithmout_id, '0')


    def urllib_exception_tester(self, exc, fn, msg, params):
        ''' Creates an exception in urllib.request.urlopen() read() and
            tests for the correct warning message
        :param exc: exception that is to be created
        :param fn: NVCLReader function to be tested
        :param msg: warning message to test for
        :param params: dictionary of parameters for 'fn'
        '''
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            open_obj.__enter__.return_value.read.side_effect = exc
            open_obj.__enter__.return_value.read.return_value = '' 
            with self.assertLogs('nvcl_kit.reader', level='WARN') as nvcl_log:
                imagelog_data_list = fn(**params)
                self.assertIn(msg, nvcl_log.output[0])
    

    def test_imagelog_exception(self):
        ''' Tests exception handling in get_imagelog_data()
        '''
        rdr = self.setup_reader()
        self.urllib_exception_tester(HTTPException, rdr.get_imagelog_data, 'HTTP Error:', {'nvcl_id':'dummy-id'})
        self.urllib_exception_tester(OSError, rdr.get_imagelog_data, 'OS Error:', {'nvcl_id':'dummy-id'})

        
    def test_profilometer_data(self):
        ''' Test get_profilometer_data()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                prof_data_list = rdr.get_profilometer_data("blah")
                self.assertEqual(len(prof_data_list), 1)

                self.assertEqual(prof_data_list[0].log_id, 'a61b105c-31e8-4da7-b790-4f21c9341c5')
                self.assertEqual(prof_data_list[0].log_name, 'Profile log')
                self.assertEqual(prof_data_list[0].max_val, 78.40174)
                self.assertEqual(prof_data_list[0].min_val, 0.001537323)
                self.assertEqual(prof_data_list[0].floats_per_sample, 128)
                self.assertEqual(prof_data_list[0].sample_count, 30954)


    def test_profilometer_exception(self):
        ''' Tests exception handling in get_profilometer_data()
        '''
        rdr = self.setup_reader()
        self.urllib_exception_tester(HTTPException, rdr.get_profilometer_data, 'HTTP Error:', {'nvcl_id':'dummy-id'})
        self.urllib_exception_tester(OSError, rdr.get_profilometer_data, 'OS Error:', {'nvcl_id':'dummy-id'})


    def test_logs_scalar(self):
        ''' Tests get_logs_scalar()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('logcoll_scalar.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                log_list = rdr.get_logs_scalar("blah")
                self.assertEqual(len(log_list), 4)
                self.assertEqual(log_list[0].log_id, '2023a603-7b31-4c97-ad59-efb220d93d9')
                self.assertEqual(log_list[0].log_name, 'Tray')
                self.assertEqual(log_list[0].is_public, 'true')
                self.assertEqual(log_list[0].log_type, '1')
                self.assertEqual(log_list[0].algorithm_id, '0')


    def test_logs_scalar_empty(self):
        ''' Tests get_logs_scalar() with an empty response
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('logcoll_empty.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                log_list = rdr.get_logs_scalar("blah")
                self.assertEqual(len(log_list), 0)


    def test_logs_scalar_exception(self):
        ''' Tests exception handling in get_logs_scalar()
        '''
        rdr = self.setup_reader()
        self.urllib_exception_tester(HTTPException, rdr.get_logs_scalar, 'HTTP Error:', {'dataset_id':'dummy-id'})
        self.urllib_exception_tester(OSError, rdr.get_logs_scalar, 'OS Error:', {'dataset_id':'dummy-id'})



    def test_logs_mosaic(self):
        ''' Tests get_logs_mosaic()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('logcoll_mosaic.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                log_list = rdr.get_logs_mosaic("blah")
                self.assertEqual(len(log_list), 4)
                self.assertEqual(log_list[0].log_id, '5f14ca9c-6d2d-4f86-9759-742dc738736')
                self.assertEqual(log_list[0].log_name, 'Mosaic')
                self.assertEqual(log_list[0].sample_count, 1)


    def test_logs_mosaic_empty(self):
        ''' Tests get_logs_mosaic() with an empty response
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('logcoll_empty.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                log_list = rdr.get_logs_mosaic("blah")
                self.assertEqual(len(log_list), 0)


    def test_logs_mosaic_exception(self):
        ''' Tests exception handling in get_logs_mosaic()
        '''
        rdr = self.setup_reader()
        self.urllib_exception_tester(HTTPException, rdr.get_logs_mosaic, 'HTTP Error:', {'dataset_id':'dummy-id'})
        self.urllib_exception_tester(OSError, rdr.get_logs_mosaic, 'OS Error:', {'dataset_id':'dummy-id'})


    def test_datasetid_list(self):
        ''' Test get_datasetid_list()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                dataset_id_list = rdr.get_datasetid_list("blah")
                self.assertEqual(len(dataset_id_list), 1)
                self.assertEqual(dataset_id_list[0], 'a4c1ed7f-1e87-444a-90ae-3fe5abf9081')


    def test_datasetid_list_empty(self):
        ''' Test get_datasetid_list() with an empty response
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll_empty.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                dataset_id_list = rdr.get_datasetid_list("blah")
                self.assertEqual(len(dataset_id_list), 0)


    def test_datasetid_list_exception(self):
        ''' Tests exception handling in get_datasetid_list()
        '''
        rdr = self.setup_reader()
        self.urllib_exception_tester(HTTPException, rdr.get_datasetid_list, 'HTTP Error:', {'nvcl_id':'dummy-id'})
        self.urllib_exception_tester(OSError, rdr.get_datasetid_list, 'OS Error:', {'nvcl_id':'dummy-id'})


    def test_dataset_list(self):
        ''' Test get_dataset_list()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                dataset_data_list = rdr.get_dataset_list("blah")
                self.assertEqual(len(dataset_data_list), 1)
                ds = dataset_data_list[0]
                self.assertEqual(ds.dataset_id, 'a4c1ed7f-1e87-444a-90ae-3fe5abf9081')
                self.assertEqual(ds.dataset_name, '6315_HP4_Mt_Block')
                self.assertEqual(ds.borehole_uri, 'http://www.blah.blah.gov.au/resource/feature/blah/borehole/6315')
                self.assertEqual(ds.tray_id, '2023a603-7b31-4c97-ad59-efb220d93d9')
                self.assertEqual(ds.section_id, '6c6b3980-8ef3-4d4e-a509-996e4f97973')
                self.assertEqual(ds.domain_id, '1186d6e5-3102-4e60-a077-e17b8ea1079')

    def test_dataset_list_empty(self):
        ''' Test get_dataset_list() with an empty response
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll_empty.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                dataset_list = rdr.get_dataset_list("blah")
                self.assertEqual(len(dataset_list), 0)


    def test_dataset_list_exception(self):
        ''' Tests exception handling in get_dataset_list()
        '''
        rdr = self.setup_reader()
        self.urllib_exception_tester(HTTPException, rdr.get_dataset_list, 'HTTP Error:', {'nvcl_id':'dummy-id'})
        self.urllib_exception_tester(OSError, rdr.get_dataset_list, 'OS Error:', {'nvcl_id':'dummy-id'})


        
    def test_spectrallog_data(self):
        ''' Test get_spectrallog_data()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = fp.read()
                spectral_data_list = rdr.get_spectrallog_data("blah")
                self.assertEqual(len(spectral_data_list), 15)
                self.assertEqual(spectral_data_list[0].log_id, '869f6712-f259-4267-874d-d341dd07bd5')
                self.assertEqual(spectral_data_list[0].log_name, 'Reflectance')
                self.assertEqual(spectral_data_list[0].wavelength_units, 'nm')
                self.assertEqual(spectral_data_list[0].sample_count, 30954)
                self.assertEqual(spectral_data_list[0].script, {'dscl': '0.000000', 'which': '64', 'prenorm': '0', 'postnorm': '0', 'bkrem': '0', 'sgleft': '0', 'sgright': '0', 'sgpoly': '0', 'sgderiv': '0'})
                self.assertEqual(spectral_data_list[0].script_raw, 'dscl=0.000000; which=64; prenorm=0; postnorm=0; bkrem=0; sgleft=0; sgright=0; sgpoly=0; sgderiv=0;')
                self.assertEqual(len(spectral_data_list[0].wavelengths), 531)
                self.assertEqual(spectral_data_list[0].wavelengths[1], 384.0)


    def test_spectrallog_exception(self):
        ''' Tests exception handling in get_spectrallog_data()
        '''
        rdr = self.setup_reader()
        self.urllib_exception_tester(HTTPException, rdr.get_spectrallog_data, 'HTTP Error:', {'nvcl_id':'dummy-id'})
        self.urllib_exception_tester(OSError, rdr.get_spectrallog_data, 'OS Error:', {'nvcl_id':'dummy-id'})


    def test_borehole_data(self):
        ''' Test get_borehole_data()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('bh_data.txt') as fp:
                open_obj.__enter__.return_value.read.return_value = bytes(fp.read(), 'ascii')
                bh_data_list = rdr.get_borehole_data("dummy-id", 10.0, "dummy-class")
                self.assertEqual(len(bh_data_list), 28)
                self.assertEqual(bh_data_list[5.0].className, 'dummy-class')
                self.assertEqual(bh_data_list[5.0].classText, 'WHITE-MICA')
                self.assertEqual(bh_data_list[5.0].colour, (1.0, 1.0, 0.0, 1.0))

                self.assertEqual(bh_data_list[275.0].className, 'dummy-class')
                self.assertEqual(bh_data_list[275.0].classText, 'WHITE-MICA')
                self.assertEqual(bh_data_list[275.0].colour, (1.0, 1.0, 0.0, 1.0))


    def test_borehole_exception(self):
        ''' Tests exception handling in get_borehole_data()
        '''
        rdr = self.setup_reader()
        self.urllib_exception_tester(HTTPException, rdr.get_borehole_data, 'HTTP Error:', {'log_id': 'dummy-logid', 'height_resol': 20, 'class_name': 'dummy-class'})
        self.urllib_exception_tester(OSError, rdr.get_borehole_data, 'OS Error:',  {'log_id': 'dummy-logid', 'height_resol': 20, 'class_name': 'dummy-class'})


if __name__ == '__main__':
    unittest.main()
