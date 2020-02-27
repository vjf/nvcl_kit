"""
# This module is used to extract NVCL borehole data
"""

import sys

import xml.etree.ElementTree as ET
import json
from collections import OrderedDict
import itertools
import logging
from types import SimpleNamespace

from requests.exceptions import RequestException

from owslib.wfs import WebFeatureService
from owslib.fes import PropertyIsLike, etree
from owslib.util import ServiceException

from http.client import HTTPException

from nvcl_kit.svc_interface import ServiceInterface

ENFORCE_IS_PUBLIC = True
''' Enforce the 'is_public' flag , i.e. any data with 'is_public' set to 'false'
    will be ignored
'''

LOG_LVL = logging.INFO
''' Initialise debug level
'''

# Set up debugging
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(LOG_LVL)

if not LOGGER.hasHandlers():

    # Create logging console handler
    HANDLER = logging.StreamHandler(sys.stdout)

    # Create logging formatter
    FORMATTER = logging.Formatter('%(name)s -- %(levelname)s - %(message)s')

    # Add formatter to ch
    HANDLER.setFormatter(FORMATTER)

    # Add handler to LOGGER and set level
    LOGGER.addHandler(HANDLER)

# Namespaces for WFS Borehole response
NS = {'wfs':"http://www.opengis.net/wfs",
      'xs':"http://www.w3.org/2001/XMLSchema",
      'it.geosolutions':"http://www.geo-solutions.it",
      'mo':"http://xmlns.geoscience.gov.au/minoccml/1.0",
      'topp':"http://www.openplans.org/topp",
      'mt':"http://xmlns.geoscience.gov.au/mineraltenementml/1.0",
      'nvcl':"http://www.auscope.org/nvcl",
      'gsml':"urn:cgi:xmlns:CGI:GeoSciML:2.0",
      'ogc':"http://www.opengis.net/ogc",
      'gsmlp':"http://xmlns.geosciml.org/geosciml-portrayal/4.0",
      'sa':"http://www.opengis.net/sampling/1.0",
      'ows':"http://www.opengis.net/ows",
      'om':"http://www.opengis.net/om/1.0",
      'xlink':"http://www.w3.org/1999/xlink",
      'gml':"http://www.opengis.net/gml",
      'er':"urn:cgi:xmlns:GGIC:EarthResource:1.1",
      'xsi':"http://www.w3.org/2001/XMLSchema-instance",
      'gml32':"http://www.opengis.net/gml/3.2"}


# From GeoSciML BoreholeView 4.1
GSMLP_IDS = ['identifier', 'name', 'description', 'purpose', 'status', 'drillingMethod',
             'operator', 'driller', 'drillStartDate', 'drillEndDate', 'startPoint',
             'inclinationType', 'boreholeMaterialCustodian', 'boreholeLength_m',
             'elevation_m', 'elevation_srs', 'positionalAccuracy', 'source', 'parentBorehole_uri',
             'metadata_uri', 'genericSymbolizer']



TIMEOUT = 6000
''' Timeout for querying WFS and NVCL services (seconds)
'''


def bgr2rgba(bgr):
    ''' Converts BGR colour integer into an RGB tuple

    :param bgr: BGR colour integer
    :returns: RGBA float tuple
    '''
    return ((bgr & 255)/255.0, ((bgr & 65280) >> 8)/255.0, (bgr >> 16)/255.0, 1.0)


class NVCLReader:
    ''' A class to extract NVCL borehole data (see README.md for details)
    '''

    def __init__(self, param_obj, wfs=None, log_lvl=None):
        '''
        :param param_obj: SimpleNamespace() object with parameters
        Fields are: 
          NVCL_URL - URL of NVCL service
          WFS_URL - URL of WFS service, GeoSciML V4.1 BoreholeView
          WFS_VERSION - (optional - default "1.1.0")
          BOREHOLE_CRS - (optional - default "EPSG:4326")
          BBOX - (optional - default {"west": -180.0,"south": -90.0,"east": 180.0,"north": 0.0}) bounding box in EPSG:4326, only boreholes within box are retrieved
          MAX_BOREHOLES - (optional - default 0) Maximum number of boreholes to retrieve. If < 1 then all boreholes are loaded

        e.g.
        from types import SimpleNamespace
        param_obj = SimpleNamespace()
        # Uses EPSG:4326
        param_obj.BBOX = { "west": 132.76, "south": -28.44, "east": 134.39, "north": -26.87 }
        param_obj.WFS_URL = "http://blah.blah.blah/geoserver/wfs"
        param_obj.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
        param_obj.MAX_BOREHOLES = 20

        :param wfs: optional owslib 'WebFeatureService' object
        :param log_lvl: optional logging level (see 'logging' package),
                        default is logging.INFO

        NOTE: Check if 'wfs' is not 'None' to see if this instance initialised properly

        '''
        # Set log level
        if log_lvl and isinstance(log_lvl, int):
            LOGGER.setLevel(log_lvl)
        self.wfs = None
        self.borehole_list = []

        # Check param_obj
        if not isinstance(param_obj, SimpleNamespace):
            LOGGER.warning("'param_obj' is not a SimpleNamespace() object")
            return
        self.param_obj = param_obj

        # If BBOX not defined, use default
        if not hasattr(self.param_obj, 'BBOX'):
            self.param_obj.BBOX = {"west": -180.0,"south": -90.0,"east": 180.0,"north": 0.0}
        else:
            if not isinstance(self.param_obj.BBOX, dict):
                LOGGER.warning("'BBOX' parameter is not a dict")
                return
            # Check BBOX dict values
            for dir in ["west", "south", "east", "north"]:
                if dir not in self.param_obj.BBOX:
                    LOGGER.warning("BBOX['%s'] parameter is missing", dir)
                    return
                if not isinstance(self.param_obj.BBOX[dir], float) and \
                   not isinstance(self.param_obj.BBOX[dir], int):
                    LOGGER.warning("BBOX['%s'] parameter is not a number", dir)
                    return

        # Check WFS_URL value
        if not hasattr(self.param_obj, 'WFS_URL'):
            LOGGER.warning("'WFS_URL' parameter is missing")
            return
        if not isinstance(self.param_obj.WFS_URL, str):
            LOGGER.warning("'WFS_URL' parameter is not a string")
            return

        # Check NVCL_URL value
        if not hasattr(self.param_obj, 'NVCL_URL'):
            LOGGER.warning("'NVCL_URL' parameter is missing")
            return
        if not isinstance(self.param_obj.NVCL_URL, str):
            LOGGER.warning("'NVCL_URL' parameter is not a string")
            return

        # Roughly check BOREHOLE_CRS EPSG: value
        if not hasattr(self.param_obj, 'BOREHOLE_CRS'):
            self.param_obj.BOREHOLE_CRS = "EPSG:4326" # "EPSG:4283"
        elif not isinstance(self.param_obj.BOREHOLE_CRS, str) or \
             "EPSG:" not in self.param_obj.BOREHOLE_CRS.upper() or \
             not self.param_obj.BOREHOLE_CRS[-4:].isnumeric():
            LOGGER.warning("'BOREHOLE_CRS' parameter is not an EPSG string")
            return

        # Roughly check WFS_VERSION value
        if not hasattr(self.param_obj, 'WFS_VERSION'):
            self.param_obj.WFS_VERSION = "1.1.0"
        elif not isinstance(self.param_obj.WFS_VERSION, str) or \
             not self.param_obj.WFS_VERSION[0].isdigit():
            LOGGER.warning("'WFS_VERSION' parameter is not a numeric string")
            return

        # Check MAX_BOREHOLES value
        if not hasattr(self.param_obj, 'MAX_BOREHOLES'):
            self.param_obj.MAX_BOREHOLES = 0
        if not isinstance(self.param_obj.MAX_BOREHOLES, int):
            LOGGER.warning("'MAX_BOREHOLES' parameter is not an integer")
            return

        # Check USE_LOCAL_FILTERING
        if not hasattr(self.param_obj, 'USE_LOCAL_FILTERING'):
            self.param_obj.USE_LOCAL_FILTERING = False
        if not isinstance(self.param_obj.USE_LOCAL_FILTERING, bool):
            LOGGER.warning("'USE_LOCAL_FILTERING' parameter is not boolean")
            return

        # If owslib wfs is not supplied
        if wfs is None:
            try:
                self.wfs = WebFeatureService(self.param_obj.WFS_URL,
                                             version=self.param_obj.WFS_VERSION,
                                             xml=None, timeout=TIMEOUT)
            except ServiceException as se_exc:
                LOGGER.warning("WFS error: %s", str(se_exc))
            except RequestException as re_exc:
                LOGGER.warning("Request error: %s", str(re_exc))
            except HTTPException as he_exc:
                LOGGER.warning("HTTP error code returned: %s", str(he_exc))
            except OSError as os_exc:
                LOGGER.warning("OS Error: %s", str(os_exc))
        else:
            self.wfs = wfs
        if self.wfs and not self._fetch_borehole_list():
            self.wfs = None

        self.svc = ServiceInterface(self.param_obj.NVCL_URL, TIMEOUT)


    def get_borehole_data(self, log_id, height_resol, class_name):
        ''' Retrieves borehole mineral data for a borehole

        :param log_id: borehole log identifier, string e.g. 'ce2df1aa-d3e7-4c37-97d5-5115fc3c33d' This is the first id from the list of triplets [log id, log type, log name] fetched from 'get_imagelog_data()'
        :param height_resol: height resolution, float
        :param class_name: name of mineral class
        :returns: dict: key - depth, float; value - SimpleNamespace( 'colour'= RGBA float tuple, 'className'= class name, 'classText'= mineral name )
        '''
        LOGGER.debug(" get_borehole_data(%s, %d, %s)", log_id, height_resol, class_name)
        # Send HTTP request, get response
        json_data = self.svc.get_downsampled_data(log_id,
            interval=height_resol, outputformat='json',
            startdepth=0.0, enddepth=10000.0)
        if not json_data:
            LOGGER.debug("get_borehole_data() json_data= %s", repr(json_data))
            return OrderedDict()
        LOGGER.debug('json_data = %s', json_data[:100])
        meas_list = []
        depth_dict = OrderedDict()
        try:
            meas_list = json.loads(json_data.decode('utf-8'))
        except json.decoder.JSONDecodeError:
            LOGGER.warning("Logid not known")
        else:
            # Sort then group by depth
            sorted_meas_list = sorted(meas_list, key=lambda x: x['roundedDepth'])
            for depth, group in itertools.groupby(sorted_meas_list, lambda x: x['roundedDepth']):
                # Filter out invalid values
                filtered_group = itertools.filterfalse(lambda x: x['classText'].upper() == 'INVALID',
                                                       group)
                # Make a dict keyed on depth, value is element with largest count
                try:
                    max_elem = max(filtered_group, key=lambda x: x['classCount'])
                except ValueError:
                    # Sometimes 'filtered_group' is empty
                    LOGGER.warning("No valid values at depth %s", str(depth))
                    continue
                col = bgr2rgba(max_elem['colour'])
                kv_dict = {'className': class_name, **max_elem, 'colour': col}
                del kv_dict['roundedDepth']
                del kv_dict['classCount']
                depth_dict[depth] = SimpleNamespace()
                for key, val in kv_dict.items():
                    setattr(depth_dict[depth], key, val)

        LOGGER.debug("get_borehole_data() Returning %s", repr(depth_dict))
        return depth_dict


    def get_datasetid_list(self, nvcl_id):
        ''' Retrieves a list of dataset ids
        :param nvcl_id: NVCL 'holeidentifier' parameter, the 'nvcl_id' from each dict item retrieved from 'get_boreholes_list()' or 'get_nvcl_id_list()'
        :returns list of dataset ids
        '''
        response_str = self.svc.get_dataset_collection(nvcl_id)
        if not response_str:
            return []
        root = ET.fromstring(response_str)
        datasetid_list = []
        for child in root.findall('./Dataset'):
            dataset_id = child.findtext('./DatasetID', default=None)
            if dataset_id:
                datasetid_list.append(dataset_id)
        return datasetid_list


    def get_dataset_list(self, nvcl_id):
        ''' Retrieves a list of dataset objects
        :param nvcl_id: NVCL 'holeidentifier' parameter, the 'nvcl_id' from each dict item retrieved from 'get_boreholes_list()' or 'get_nvcl_id_list()'
        :returns list of SimpleNamespace objects, attributes are: dataset_id, dataset_name, borehole_uri, tray_id, section_id, domain_id
        '''
        response_str = self.svc.get_dataset_collection(nvcl_id)
        if not response_str:
            return []
        root = ET.fromstring(response_str)
        dataset_list = []
        for child in root.findall('./Dataset'):
            # Compulsory
            dataset_id = child.findtext('./DatasetID', default=None)
            dataset_name = child.findtext('./DatasetName', default=None)
            if not dataset_id or not dataset_name:
                continue
            # Optional
            dataset_obj = SimpleNamespace(dataset_id=dataset_id,
                                          dataset_name=dataset_name)
            for label, key in [('borehole_uri', './boreholeURI'),
                                ('tray_id', './trayID'),
                                ('section_id', './sectionID'),
                                ('domain_id', './domainID')]:
                val = child.findtext(key, default=None)
                if val:
                    setattr(dataset_obj, label, val)
            dataset_list.append(dataset_obj)
        return dataset_list


    def get_all_imglogs(self, dataset_id):
        ''' Retrieves a list of all log objects from mosaic service

        :param dataset_id: dataset id, taken from 'get_datasetid_list()' or 'get_dataset_list()'
        :returns: list of SimpleNamespace() objects, attributes are: log_id, log_name, sample_count. On error returns empty list
        '''
        return self._filter_mosaic_logs(dataset_id)


    def get_mosaic_imglogs(self, dataset_id):
        ''' Retrieves a list of 'Mosaic' log objects from mosaic service

        :param dataset_id: dataset id, taken from 'get_datasetid_list()' or 'get_dataset_list()'
        :return: list of SimpleNamespace objects. Fields are: 'log_id', 'log_name', 'sample_count'. On error returns an empty list.
        '''
        return self._filter_mosaic_logs(dataset_id, 'Mosaic')


    def get_tray_thumb_imglogs(self, dataset_id):
        ''' Retrieves a list of 'Tray Thumbnail Images' log objects from mosaic service

        :param dataset_id: dataset id, taken from 'get_datasetid_list()' or 'get_dataset_list()'
        :return: list of SimpleNamespace objects. Fields are: 'log_id', 'log_name', 'sample_count'. On error returns an empty list.
        '''
        return self._filter_mosaic_logs(dataset_id, 'Tray Thumbnail Images')


    def get_tray_imglogs(self, dataset_id):
        ''' Retrieves 'Tray Image' log objects from mosaic service

        :param dataset_id: dataset id, taken from 'get_datasetid_list()' or 'get_dataset_list()'
        :return: list of SimpleNamespace objects. Fields are: 'log_id', 'log_name', 'sample_count'. On error returns an empty list.
        '''
        return self._filter_mosaic_logs(dataset_id, 'Tray Images')


    def get_imagery_imglogs(self, dataset_id):
        ''' Retrieves 'Imagery' log objects from mosaic service

        :param dataset_id: dataset id, taken from 'get_datasetid_list()' or 'get_dataset_list()'
        :return: list of SimpleNamespace objects. Fields are: 'log_id', 'log_name', 'sample_count'. On error returns an empty list.
        '''

        return self._filter_mosaic_logs(dataset_id, 'Imagery')


    def _filter_mosaic_logs(self, dataset_id, target_log_name='*'):
        ''' Retrieves logs with a particular name using log collection mosaic service

        :param dataset_id: dataset id, taken from 'get_datasetid_list()' or 'get_dataset_list()'
        :param target_log_name: (optional) log name to search for. Default is '*' which retrieves all logs
        :return: list of SimpleNamespace objects. Fields are: log_id, log_name, sample_count
        '''
        response_str = self.svc.get_log_collection(dataset_id, True)
        if not response_str:
            return []
        root = ET.fromstring(response_str)
        dataset_list = []
        for child in root.findall('./Log'):
            log_id = child.findtext('./LogID', default=None)
            log_name = child.findtext('./LogName', default=None)
            try:
                sample_count = int(child.findtext('./SampleCount', default=0))
            except ValueError:
                sample_count = 0.0
            if not log_id or not log_name:
                continue
            if target_log_name.lower() == log_name.lower() or target_log_name=='*':
                dataset_obj = SimpleNamespace(log_id=log_id,
                                          log_name=log_name,
                                          sample_count=sample_count)
                dataset_list.append(dataset_obj)
        return dataset_list


    def get_mosaic_image(self, log_id, **options):
        ''' Retrieves images of NVCL core trays

        :param log_id: obtained through calling 'get_mosaic_imglogs()' or 'get_tray_thumb_imglogs()' or 'get_tray_image_imglogs()' or 'get_imagery_imglogs()'
        :param options: optional parameters:
                 width: number of column the images are to be displayed, default value=3
                 startsampleno: the first sample image to be displayed, default value=0
                 endsampleno: the last sample image to be displayed, default value=99999
        '''
        return self.svc.get_mosaic(log_id, **options)


    def get_tray_thumb_html(self, dataset_id, log_id, **options):
        ''' Gets core tray thumbnail images as HTML

        :param dataset_id: obtained through calling 'get_datasetid_list()'
        :param log_id: obtained through calling 'get_tray_thumb_imglogs()'
        :param width: specify the number of column the images are to be displayed, default value=3
        :param startsampleno: the first sample image to be displayed, default value=0
        :param endsampleno: the last sample image to be displayed, default value=99999
        :return: thumbnail image in HTML format
        '''
        return self.svc.get_mosaic_tray_thumbnail(dataset_id, log_id, **options)


    def get_tray_thumb_jpg(self, log_id, sample_no='0'):
        ''' Gets core tray thumbnail images as JPEG

        :param log_id: obtained through calling 'get_tray_thumb_imglogs()'
        :param sample_no: sample number, string e.g. '0','1','2'...  optional, default is '0'
        :return: thumbnail image in PNG format
        '''
        return self.svc.get_display_tray_thumb(log_id, sample_no)


    def get_tray_depths(self, log_id):
        ''' Gets tray depths
        :param log_id: obtained through calling 'get_tray_thumb_imglogs()' or 'get_tray_imglogs()'
        :return: a list of SimpleNamespace objects, with attributes: 'sample_no', 'start_value' and 'end_value'
        '''
        response_str = self.svc.get_image_tray_depth(log_id)
        if not response_str:
            return []
        root = ET.fromstring(response_str)
        image_tray_list = []
        for child in root.findall('./ImageTray'):
            sample_no = child.findtext('./SampleNo', default=None)
            start_value = child.findtext('./StartValue', default=None)
            end_value = child.findtext('./EndValue', default=None)
            if not sample_no or not start_value or not end_value:
                continue
            image_tray_obj = SimpleNamespace(sample_no=sample_no,
                                          start_value=start_value,
                                          end_value=end_value)
            image_tray_list.append(image_tray_obj)
        return image_tray_list


    def get_scalar_logs(self, dataset_id):
        ''' Retrieves a list of log objects for scalar plot service

        :param dataset_id: dataset_id, taken from 'get_datasetid_list()' or 'get_dataset_list()'
        :returns: list of SimpleNamespace() objects, attributes are: log_id, log_name, is_public, log_type, algorithm_id. On error returns empty list
        '''
        response_str = self.svc.get_log_collection(dataset_id)
        if not response_str:
            return []
        root = ET.fromstring(response_str)
        log_list = []
        for child in root.findall('./Log'):
            log_id = child.findtext('./LogID', default=None)
            log_name = child.findtext('./logName', default=None)
            is_public = child.findtext('./ispublic', default=None)
            if ENFORCE_IS_PUBLIC and is_public and is_public.upper() == 'FALSE':
                continue
            log_type = child.findtext('./logType', default=None)
            algorithm_id = child.findtext('./algorithmoutID', default=None)
            # Only types 1,2,5,6 can be used
            if log_id and log_name and log_type in ['1','2','5','6'] \
                                                             and algorithm_id:
                log = SimpleNamespace(log_id=log_id,
                                      log_name=log_name,
                                      is_public=is_public,
                                      log_type=log_type,
                                      algorithm_id=algorithm_id)
                log_list.append(log)
        return log_list


    def get_scalar_data(self, log_id_list):
        ''' Downloads scalar data in CSV format

        :param log_id_list: list of log ids obtained through calling 'get_scalar_logs()'
        :return: scalar data in CSV format
        '''
        return self.svc.download_scalar(log_id_list)


    def get_sampled_scalar_data(self, log_id, **options):
        ''' Returns data in downsampled format, to a certain height resolution

        :param log_id: obtained through calling 'get_scalar_logs()'
        :param outputformat: (optional) string 'csv' or 'json'
        :param startdepth: (optional) start of depth range, in metres from borehole
            collar
        :param enddepth: (optional) end of depth range, in metres from borehole
            collar
        :param interval: (optional) resolution to bin or average over
        '''
        return self.svc.get_downsampled_data(log_id, **options)


    def plot_scalar_png(self, log_id, **options):
        ''' Draws a plot as an image in PNG format.

        :param log_id: obtained through calling 'get_scalar_logs()'
        :param startdepth: (optional) the start depth of a borehole collar,
             default value=0
        :param enddepth: (optional) the end depth of a borehole collar,
             default value=99999
        :param samplinginterval: (optional) the interval of the sampling,
             default value=1
        :param width: (optional) the width of the image in pixel, default value=300
        :param height: (optional) the height of the image in pixel,
             default value=600
        :param graphtype: (optional) an integer range from 1 to 3,
             1=Stacked Bar Chart, 2=Scattered Chart, 3=Line Chart, default value=1
        :param legend: (optional) value=1 or 0, 1 - indicates to show the legend,
             0 to hide it, optional, default to 1
        :return: a 2d plot as a PNG image
        '''
        return self.svc.get_plot_scalar(log_id, **options)


    def plot_scalars_html(self, log_id_list, **options):
        ''' Draws multiple plots, returned in HTML format

        :param log_id_list: a list of up to 6 log ids, obtained through calling
               'get_scalar_logs()'
        :param startdepth: (optional) the start depth of a borehole collar,
             default value=0
        :param enddepth: (optional) the end depth of a borehole collar,
             default value=99999
        :param samplinginterval: (optional) the interval of the sampling,
             default value=1
        :param width: (optional) the width of the image in pixel,
             default value=300
        :param height: (optional) the height of the image in pixel,
             default value=600
        :param graphtype: (optional) an integer range from 1 to 3,
             1=Stacked Bar Chart, 2=Scattered Chart, 3=Line Chart, default value=1
        :param legend: (optional) value=yes or no, if yes - indicate to show the
             legend, default to yes
        :return: one or more 2d plots as HTML
        '''
        # NB: Service only plots the first 6 log ids
        return self.svc.get_plot_multi_scalar(log_id_list[:6], **options)


    def get_imagelog_data(self, nvcl_id):
        ''' Retrieves a set of image log data for a particular borehole

        :param nvcl_id: NVCL 'holeidentifier' parameter,
                        the 'nvcl_id' from each dict item retrieved from 'get_boreholes_list()' or 'get_nvcl_id_list()'
        :returns: a list of SimpleNamespace() objects with attributes:
                  log_id, log_type, log_name
        '''
        response_str = self.svc.get_dataset_collection(nvcl_id)
        if not response_str:
            return []
        root = ET.fromstring(response_str)
        logid_list = []
        for child in root.findall('./*/Logs/Log'):
            is_public = child.findtext('./ispublic', default='false')
            log_name = child.findtext('./logName', default='')
            log_type = child.findtext('./logType', default='')
            log_id = child.findtext('./LogID', default='')
            alg_id = child.findtext('./algorithmoutID', default='')
            if (is_public == 'true' or not ENFORCE_IS_PUBLIC) and \
                      log_name != '' and log_type != '' and log_id != '':
                logid_list.append(SimpleNamespace(log_id=log_id, log_type=log_type, log_name=log_name, algorithmout_id=alg_id))
        return logid_list


    def get_spectrallog_data(self, nvcl_id):
        ''' Retrieves a set of spectral log data for a particular borehole

        :param nvcl_id: NVCL 'holeidentifier' parameter,
                        the 'nvcl_id' from each dict item retrieved from 'get_boreholes_list()' or 'get_nvcl_id_list()'
        :returns: a list of SimpleNamespace() objects with attributes:
                  log_id, log_name, wavelength_units, sample_count, script,
                  wavelengths
        '''
        response_str = self.svc.get_dataset_collection(nvcl_id)
        if not response_str:
            return []
        root = ET.fromstring(response_str)
        logid_list = []
        for child in root.findall('./*/SpectralLogs/SpectralLog'):
            log_id = child.findtext('./logID', default='')
            log_name = child.findtext('./logName', default='')
            wavelength_units = child.findtext('./wavelengthUnits', default='')
            try:
                sample_count = int(child.findtext('./sampleCount', default=0))
            except ValueError:
                sample_count = 0
            script_raw = child.findtext('./script', default='')
            script_str = script_raw.replace('; ',';')
            script_str_list = script_str.split(';')
            script_dict = {}
            for assgn in script_str_list:
                var, eq, val = assgn.partition('=')
                if var and eq == '=':
                    script_dict[var] = val
            wavelengths = child.findtext('./wavelengths', default='')
            try:
                wv_list = [ float(wv_str) for wv_str in wavelengths.split(',') ]
            except ValueError:
                wv_list = []
            logid_list.append(SimpleNamespace(log_id=log_id, log_name=log_name, wavelength_units=wavelength_units, sample_count=sample_count, script_raw=script_raw, script=script_dict, wavelengths=wv_list))
        return logid_list


    def get_profilometer_data(self, nvcl_id):
        ''' Retrieves a set of profilometer logs for a particular borehole

        :param nvcl_id: NVCL 'holeidentifier' parameter,
                        the 'nvcl_id' from each dict item retrieved from 'get_boreholes_list()' or 'get_nvcl_id_list()'
        :returns: a list of SimpleNamespace() objects with attributes:
                  log_id, log_name, sample_count, floats_per_sample, 
                  min_val, max_val
        '''
        response_str = self.svc.get_dataset_collection(nvcl_id)
        if not response_str:
            return []
        root = ET.fromstring(response_str)
        logid_list = []
        for child in root.findall('./*/ProfilometerLogs/ProfLog'):
            log_id = child.findtext('./logID', default='')
            log_name = child.findtext('./logName', default='')
            try:
                sample_count = int(child.findtext('./sampleCount', default=0))
            except ValueError:
                sample_count = 0.0
            try:
                floats_per_sample = float(child.findtext('./floatsPerSample', default=0.0))
            except ValueError:
                floats_per_sample = 0.0
            try:
                min_val = float(child.findtext('./minVal', default=0.0))
            except ValueError:
                min_val = 0.0
            try:
                max_val = float(child.findtext('./maxVal', default=0.0))
            except ValueError:
                max_val = 0.0
            logid_list.append(SimpleNamespace(log_id=log_id, log_name=log_name, sample_count=sample_count, floats_per_sample=floats_per_sample, min_val=min_val, max_val=max_val))
        return logid_list


    def get_boreholes_list(self):
        ''' Returns a list of dictionary objects, extracted from WFS requests of boreholes. Fields are mostly taken from GeoSciML v4.1 Borehole View: \
            'nvcl_id', 'identifier', 'name', 'description', 'purpose', 'status', 'drillingMethod', 'operator', 'driller', 'drillStartDate', 'drillEndDate', 'startPoint', 'inclinationType', 'href', 'boreholeMaterialCustodian', 'boreholeLength_m', 'elevation_m', 'elevation_srs', 'positionalAccuracy', 'source', 'x', 'y, 'z', 'parentBorehole_uri', 'metadata_uri', 'genericSymbolizer' \
            NB: (1) Depending on the WFS, not all fields will have values
                (2) 'href' corresponds to 'gsmlp:identifier'
                (3) 'x', 'y', 'z' are x-coordinate, y-coordinate and elevation
                (4) 'nvcl_id' is the GML 'id', used as an id in the NVCL services

            :returns: a list of dictionaries whose fields correspond to a response from a WFS request of GeoSciML v4.1 BoreholeView
        '''
        return self.borehole_list  


    def get_nvcl_id_list(self):
        '''
        Returns a list of NVCL ids, can be used as input to other 'nvcl_kit' API
        calls e.g. get_spectrallog_data()

        :return: a list of NVCL id strings
        '''
        return [bh['nvcl_id'] for bh in self.borehole_list]


    def _wfs_getfeature(self):
        response_str = b''
        bhv_list = []
        # Don't use local filtering, can be both WFS v1.1.0 or v2.0.0
        if not self.param_obj.USE_LOCAL_FILTERING:
            # FIXME: Can't filter for BBOX and nvclCollection==true at the same time
            # [owslib's BBox uses 'ows:BoundingBox', not supported in WFS]
            # so is best to do the BBOX manually
            filter_ = PropertyIsLike(propertyname='gsmlp:nvclCollection', literal='true', matchCase=False)
            # filter_2 = BBox([self.param_obj.BBOX['west'], self.param_obj.BBOX['south'], self.param_obj.BBOX['east'],
            #              self.param_obj.BBOX['north']], crs=self.param_obj.BOREHOLE_CRS)
            # filter_3 = And([filter_, filter_2])
            filterxml = etree.tostring(filter_.toXML()).decode("utf-8")
            try:
                getfeat_params = { 'typename': 'gsmlp:BoreholeView', 'filter': filterxml }
                if self.param_obj.WFS_VERSION != '2.0.0':
                    getfeat_params['srsname'] = self.param_obj.BOREHOLE_CRS
                response = self.wfs.getfeature(**getfeat_params)
                response_str = bytes(response.read(), encoding='ascii')
            except (RequestException, HTTPException, ServiceException, OSError) as exc:
                LOGGER.warning("WFS GetFeature failed, filter=%s: %s", filterxml, str(exc))
                return bhv_list
            root = ET.fromstring(response_str)
            return root.findall('./*/gsmlp:BoreholeView', NS)

        elif self.param_obj.WFS_VERSION == "2.0.0":
            RECORD_INC = 10000
            record_cnt = 0
            done = False
            bhv_list = []
            while not done:
                try:
                    getfeat_params = { 'typename':'gsmlp:BoreholeView',
                                       'maxfeatures': RECORD_INC,
                                       'startindex': record_cnt}
                    # SRS name is not a parameter in v2.0.0
                    LOGGER.debug('_wfs_getfeature(): getfeat_params = %s', repr(getfeat_params))
                    response = self.wfs.getfeature(**getfeat_params)
                    resp_s = bytes(response.read(), encoding='ascii')
                    LOGGER.debug('_wfs_getfeature(): resp_s = %s', resp_s)
                except (RequestException, HTTPException, ServiceException, OSError) as exc:
                    LOGGER.warning("WFS GetFeature failed, filter=%s: %s", filterxml, str(exc))
                    return bhv_list
                record_cnt += RECORD_INC
                root = ET.fromstring(resp_s)
                bhv_list += [ x for x in root.findall('./*/gsmlp:BoreholeView', NS)]
                num_ret = root.attrib.get('numberReturned', '0')
                LOGGER.debug('_wfs_getfeature(): num_ret = %s',  num_ret)
                LOGGER.debug('record_cnt = %d', record_cnt)
                done = num_ret == '0'

            return bhv_list
        else:
            LOGGER.error("Cannot have USE_LOCAL_FILTERING and WFS_VERSION < 2.0.0")
            return []


    def _fetch_borehole_list(self):
        ''' Returns a list of WFS borehole data within bounding box, but only NVCL boreholes
            [ { 'nvcl_id': XXX, 'x': XXX, 'y': XXX, 'href': XXX, ... }, { ... } ]
            See description of 'get_borehole_list()' for more info

        :return: True if operation succeeded
        '''
        LOGGER.debug("_fetch_boreholes_list()")
        bhv_list = self._wfs_getfeature()
        if len(bhv_list)==0:
            LOGGER.debug('_fetch_boreholes_list(): No response')
            return False
        LOGGER.debug('len(bhv_list) = %d', len(bhv_list))
        LOGGER.debug('bhv_list = %s', repr(bhv_list))
        borehole_list = []
        borehole_cnt = 0
        record_cnt = 0

        for i in range(len(bhv_list)):
            LOGGER.debug('i = %d', i)
            child = bhv_list[i]
            LOGGER.debug('len(bhv_list) = %d', len(bhv_list))
            LOGGER.debug('child = %s',  ET.tostring(child))
            # WFS v2.0.0 uses gml32
            if self.param_obj.WFS_VERSION == '2.0.0':
                id_str = '{'+NS['gml32']+'}id'
            else:
                id_str = '{'+NS['gml']+'}id'
            nvcl_id = child.attrib.get(id_str, '').split('.')[-1:][0]

            # Some services don't use a namepace for their id
            if nvcl_id == '':
                nvcl_id = child.attrib.get('id', '').split('.')[-1:][0]

            is_nvcl = child.findtext('./gsmlp:nvclCollection', default="?????", namespaces=NS)
            LOGGER.debug("is_nvcl = %s", is_nvcl)
            LOGGER.debug("nvcl_id = %s", nvcl_id)
            if is_nvcl.lower() == "true":
                borehole_dict = {'nvcl_id': nvcl_id}

                # Finds borehole collar x,y assumes units are degrees
                x_y = child.findtext('./gsmlp:shape/gml:Point/gml:pos', default="? ?",
                                     namespaces=NS).split(' ')
                reverse_coords = False
                if x_y == ['?', '?']:
                    point = child.findtext('./gsmlp:shape', default="POINT(0.0 0.0)", namespaces=NS).strip(' ')
                    reverse_coords = True
                    x_y = point.partition('(')[2].rstrip(')').split(' ')
                LOGGER.debug('x_y = %s', repr(x_y))

                try:
                    if self.param_obj.BOREHOLE_CRS != 'EPSG:4326' or reverse_coords:
                        borehole_dict['y'] = float(x_y[0]) # lat
                        borehole_dict['x'] = float(x_y[1]) # lon
                    else:
                        borehole_dict['x'] = float(x_y[0]) # lon
                        borehole_dict['y'] = float(x_y[1]) # lat
                except (OSError, ValueError) as os_exc:
                    LOGGER.warning("Cannot parse collar coordinates %s", str(os_exc))
                    continue

                borehole_dict['href'] = child.findtext('./gsmlp:identifier',
                                                       default="", namespaces=NS)

                # Finds most of the borehole details
                for tag in GSMLP_IDS:
                    if tag != 'identifier':
                        borehole_dict[tag] = child.findtext('./gsmlp:'+tag, default="",
                                                            namespaces=NS)

                elevation = child.findtext('./gsmlp:elevation_m', default="0.0", namespaces=NS)
                try:
                    borehole_dict['z'] = float(elevation)
                except ValueError:
                    borehole_dict['z'] = 0.0

                LOGGER.debug('borehole_dict = %s', repr(borehole_dict))
                LOGGER.debug('%s < %s, %s > %s', self.param_obj.BBOX['west'], borehole_dict['x'],
                                                 self.param_obj.BBOX['east'], borehole_dict['x'])
                LOGGER.debug('%s > %s, %s < %s', self.param_obj.BBOX['north'], borehole_dict['y'],
                                                 self.param_obj.BBOX['south'], borehole_dict['y'])

                # Only accept if within bounding box
                if self.param_obj.BBOX['west'] < borehole_dict['x'] and \
                   self.param_obj.BBOX['east'] > borehole_dict['x'] and \
                   self.param_obj.BBOX['north'] > borehole_dict['y'] and \
                   self.param_obj.BBOX['south'] < borehole_dict['y']:
                    borehole_cnt += 1
                    self.borehole_list.append(borehole_dict)
                    LOGGER.debug("borehole_cnt = %d", borehole_cnt)

                if self.param_obj.MAX_BOREHOLES > 0 and borehole_cnt >= self.param_obj.MAX_BOREHOLES:
                    break
            record_cnt += 1
            LOGGER.debug('record_cnt = %d', record_cnt)
        LOGGER.debug('_fetch_boreholes_list() returns True')
        return True
