#!/usr/bin/env python3
import sys, os
import unittest
from unittest.mock import patch, Mock
from requests.exceptions import Timeout, RequestException
from owslib.util import ServiceException
from http.client import HTTPException

from types import SimpleNamespace

from nvcl_kit.reader import NVCLReader

MAX_BOREHOLES = 20

class TestNVCLReader(unittest.TestCase):


    def setup_param_obj(self, max_boreholes, bbox={"west": -180.0,"south": -90.0,"east": 180.0,"north": 0.0}):
        ''' Create a parameter object for passing to NVCLReader constructor
 
        :param max_boreholes: maximum number of boreholes to download
        :returns: SimpleNamespace() object containing parameters
        '''
        param_obj = SimpleNamespace()
        param_obj.BBOX = bbox
        param_obj.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
        param_obj.BOREHOLE_CRS = "EPSG:4283"
        param_obj.WFS_VERSION = "1.1.0"
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.MAX_BOREHOLES = max_boreholes
        return param_obj


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
            param_obj = self.setup_param_obj(MAX_BOREHOLES)
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
            param_obj = self.setup_param_obj(MAX_BOREHOLES)
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
            wfs_resp_str = fp.readline()
            wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str
            param_obj = self.setup_param_obj(MAX_BOREHOLES)
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
            wfs_resp_list = fp.readlines()
            wfs_resp_str = ''.join(wfs_resp_list)
            wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str.rstrip('\n')
            param_obj = self.setup_param_obj(MAX_BOREHOLES)
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
            wfs_resp_list = fp.readlines()
            wfs_resp_str = ''.join(wfs_resp_list)
            wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str.rstrip('\n')
            param_obj = self.setup_param_obj(0)
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
            wfs_resp_list = fp.readlines()
            wfs_resp_str = ''.join(wfs_resp_list)
            wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str.rstrip('\n')
            param_obj = self.setup_param_obj(0, bbox={"west": 146.0,"south": -41.2,"east": 147.2,"north": -40.5})
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
            wfs_resp_list = fp.readlines()
            wfs_resp_str = ''.join(wfs_resp_list)
            wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str.rstrip('\n')
            param_obj = self.setup_param_obj(0)
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
                wfs_resp_list = fp.readlines()
                wfs_resp_str = ''.join(wfs_resp_list)
                wfs_obj.getfeature.return_value.read.return_value = wfs_resp_str.rstrip('\n')
                param_obj = self.setup_param_obj(0)
                rdr = NVCLReader(param_obj)
        return rdr 
   

    def test_imagelog_data(self):
        ''' Test get_imagelog_data()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                resp_list = fp.readlines()
                resp_str = ''.join(resp_list)
                open_obj.__enter__.return_value.read.return_value = resp_str 
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
                resp_list = fp.readlines()
                resp_str = ''.join(resp_list)
                open_obj.__enter__.return_value.read.return_value = resp_str 
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

        
    def test_spectrallog_data(self):
        ''' Test get_spectrallog_data()
        '''
        rdr = self.setup_reader()
        with unittest.mock.patch('urllib.request.urlopen') as mock_request:
            open_obj = mock_request.return_value
            with open('dataset_coll.txt') as fp:
                resp_list = fp.readlines()
                resp_str = ''.join(resp_list)
                open_obj.__enter__.return_value.read.return_value = resp_str 
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
                resp_list = fp.readlines()
                resp_str = ''.join(resp_list)
                open_obj.__enter__.return_value.read.return_value = bytes(resp_str, 'ascii') 
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
