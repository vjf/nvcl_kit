# pynvcl

#### A simple module used to extract Australian NVCL borehole data

Requires:  [owslib](https://github.com/geopython/OWSLib)

How to extract NVCL borehole data:

**1. Instantiate class**

```python
from nvcl_kit import NVCLKit
from types import SimpleNamespace
param_obj = SimpleNamespace()
setattr(param_obj, "BBOX", { "west": 132.76, "south": -28.44, "east": 134.39, "north": -26.87 })
setattr(param_obj, "WFS_URL", "http://blah.blah.blah/nvcl/geoserver/wfs")
setattr(param_obj, "BOREHOLE_CRS", "EPSG:4283")
setattr(param_obj, "WFS_VERSION", "1.1.0")
setattr(param_obj, "NVCL_URL", "https://blah.blah.blah/nvcl/NVCLDataServices")
nvcl_obj = NVCLKit(param_obj)
```

**2. Check if 'wfs' is not 'None' to see if this instance initialised properly**

```python
if not nvcl_obj.wfs:
    print("ERROR!")
```

**3. Call get_boreholes_list() to get list of NVCL boreholes**

```python
MAX_BOREHOLES = 20
bh_list = nvcl_obj.get_boreholes_list(MAX_BOREHOLES)
```

**4. Call get_borehole_logids() to get logids**

```python
# Construct a list of NVCL ids
nvcl_id_list = [bh['nvcl_id'] for bh in bh_list]
# Get logids for first borehole in list
nvcl_id = nvcl_id_list[0]
log_id_list = nvcl_obj.get_borehole_logids(nvcl_id)
```

**5. Call get_borehole_data() to get borehole data**

```python
# Analysis class has 2 parts:
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
        bh_data = nvcl_obj.get_borehole_data(log_id, HEIGHT_RESOLUTION, ANALYSIS_CLASS)
        # Print out the colour, mineral and class name at each depth
        for depth in bh_data:
            print("At ", depth, "my class, mineral, colour is", bh_data[depth]['className'],
                  bh_data[depth]['classText'], bh_data[depth]['colour'])
```
