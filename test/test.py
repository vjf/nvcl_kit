#!/usr/bin/env python3
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
import sys, os



sys.path.append(os.path.join('..', 'nvcl_kit'))

from nvcl_kit import NVCLKit

class TestEmpty(unittest.TestCase):
    @unittest.mock.patch('nvcl_kit.WebFeatureService', autospec=True)
    def test_urllib(self, mock_wfs):
            wfs_obj = mock_wfs.return_value
            wfs_obj.getfeature.return_value = Mock()
            wfs_obj.getfeature.return_value.read.return_value = '<?xml version="1.0" encoding="UTF-8"?><wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:erl="http://xmlns.earthresourceml.org/earthresourceml-lite/1.0" xmlns:mo="http://xmlns.geoscience.gov.au/minoccml/1.0" xmlns:mt="http://xmlns.geoscience.gov.au/mineraltenementml/1.0" xmlns:nvcl="http://www.auscope.org/nvcl" xmlns:gsml="urn:cgi:xmlns:CGI:GeoSciML:2.0" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gsmlp="http://xmlns.geosciml.org/geosciml-portrayal/4.0" xmlns:sa="http://www.opengis.net/sampling/1.0" xmlns:ows="http://www.opengis.net/ows" xmlns:om="http://www.opengis.net/om/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:gml="http://www.opengis.net/gml" xmlns:er="urn:cgi:xmlns:GGIC:EarthResource:1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" numberOfFeatures="0" timeStamp="2019-11-06T22:38:24.996Z" xsi:schemaLocation="http://xmlns.geosciml.org/geosciml-portrayal/4.0 http://schemas.geoscience.gov.au/geosciml/4.0/geosciml-portrayal.xsd http://www.opengis.net/wfs http://geology.data.nt.gov.au:80/geoserver/schemas/wfs/1.1.0/wfs.xsd"><gml:featureMembers/></wfs:FeatureCollection>'
            param_obj = SimpleNamespace()
            setattr(param_obj, "BBOX", {"west": 132.76,"south": -28.44,"east": 134.39,"north": -26.87})
            setattr(param_obj, "WFS_URL", "http://blah.blah.blah/nvcl/geoserver/wfs")
            setattr(param_obj, "BOREHOLE_CRS", "EPSG:4283")
            setattr(param_obj, "WFS_VERSION", "1.1.0")
            setattr(param_obj, "NVCL_URL", "https://blah.blah.blah/nvcl/NVCLDataServices")
            kit = NVCLKit(param_obj)
            l = kit.get_boreholes_list(20)
            self.assertEqual(l, [])

if __name__ == '__main__':
    unittest.main()
