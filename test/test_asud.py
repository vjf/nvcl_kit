#!/usr/bin/env python3
import sys, os
import unittest
from unittest.mock import patch, Mock
from requests.exceptions import Timeout, RequestException
from owslib.util import ServiceException
from http.client import HTTPException
import logging

from types import SimpleNamespace

from nvcl_kit.asud import get_asud_record


class TestNVCLAsud(unittest.TestCase):

    def try_input_param(self, lon, lat, msg):
        ''' Used to test variations in erroneous input parameters
            :param lon: longitude (float)
            :param lat: latitude (float)
            :param msg: expected warning message
        '''
        with self.assertLogs('nvcl_kit.asud', level='WARN') as nvcl_log:
            rec = get_asud_record(lon, lat)
            self.assertIn(msg, nvcl_log.output[0])
            self.assertEqual(rec, None)

    def test_params(self):
        ''' Tests exception handling in get_borehole_data()
        '''
        self.try_input_param(0.0, None, 'lat parameter is not a float')
        self.try_input_param(None, 8.0, 'lon parameter is not a float')
        self.try_input_param(None, "", 'lon parameter is not a float')
