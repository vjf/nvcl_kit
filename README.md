pynvcl
======

## A simple module used to extract NVCL borehole data

Requires:  [owslib](https://github.com/geopython/OWSLib)

How to extract NVCL borehole data:

    **(1) Instantiate class**

       _from nvcl_kit import NVCLKit
       param_obj = {
            "BBOX": { "west": 132.76, "south": -28.44, "east": 134.39, "north": -26.87 },
            "MODEL_CRS": "EPSG:28352",
            "WFS_URL": "http://blah.blah.blah/nvcl/geoserver/wfs",
            "BOREHOLE_CRS": "EPSG:4283",
            "WFS_VERSION": "1.1.0",
            "NVCL_URL": "https://blah.blah.blah/nvcl/NVCLDataServices"
       }
       nvcl_obj = NVCLKit(param_obj)_    **(2) Check if 'wfs' is not 'None' to see if this instance initialised properly**

       _if not nvcl_obj.wfs:
           print("ERROR!")_

    **(3) Call get_boreholes_list() to get list of NVCL boreholes**

       _max_boreholes = 20
       bh_list = nvcl_obj.get_boreholes_list(max_boreholes)_

    **(4) Call get_borehole_logids() to get logids**

       _nvcl_id_list = [bh['nvcl_id'] for bh in bh_list]
       # Get logids for first borehole in list
       nvcl_id = nvcl_id_list[0]
       log_id_list = nvcl_obj.get_borehole_logids[nvcl_id]_   **(5) Call get_borehole_data() to get borehole data**

       _# Analysis class has 2 parts:
       # 1. Min1,2,3 = 1st, 2nd, 3rd most common mineral
       #    OR Grp1,2,3 = 1st, 2nd, 3rd most common group of minerals
       # 2. uTSAV = visible light, uTSAS = shortwave IR, uTSAT = thermal IR
       #
       # These combine to give us a class name such as 'Grp1 uTSAS'
       #
       # Here we extract data for log type '1' and 'Grp1 uTSAS'
       HEIGHT_RESOLUTION = 20.0
       ANALYSIS_CLASS = 'Grp1 uTSAS'
       LOG_TYPE = '1'
       for log_id, log_type, log_name in log_id_list:
           if log_type == LOG_TYPE and log_name == ANALYSIS_CLASS:
               bh_data = nvcl_obj.get_borehole_data(log_id, HEIGHT_RESOLUTION, ANALYSIS_CLASS)_
               # Print out the colour, mineral and class name at each depth
               for depth in bh_data:
                   print("At ", depth, "my class, mineral, colour is", bh_data[depth]['className'], bh_data[depth]['classText'], bh_data[depth]['colour'])_



       

       
       




