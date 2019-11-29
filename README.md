# nvcl_kit

#### A simple module used to read Australian NVCL borehole data

*Brief Introduction:* how to extract NVCL borehole data

**1. Instantiate class**

```python
from nvcl_kit.reader import NVCLReader 
from types import SimpleNamespace
param = SimpleNamespace()
param.BBOX = {"west": 132.76, "south": -28.44, "east": 134.39, "north": -26.87 }
param.WFS_URL = "http://blah.blah.blah/nvcl/geoserver/wfs"
param.BOREHOLE_CRS = "EPSG:4283"
param.WFS_VERSION = "1.1.0"
param.NVCL_URL = "https://blah.blah.blah/nvcl/NVCLDataServices"
param.MAX_BOREHOLES = 20
reader = NVCLReader(param)
```

**2. Check if 'wfs' is not 'None' to see if this instance initialised properly**

```python
if not reader.wfs:
    print("ERROR!")
```

**3. Call get_boreholes_list() to get list of NVCL borehole data**

```python
bh_list = reader.get_boreholes_list()
```

**4. Call get_nvcl_id_list() to get a list of NVCL borehole ids**

```python
nvcl_id_list = reader.get_nvcl_id_list()
```

**5. Using an NVCL borehole id from previous step, call get_imagelog_data()
     to get logids**

```python
# Get list of NVCL ids
nvcl_id_list = reader.get_nvcl_id_list()
# Get NVCL log id for first borehole in list
nvcl_id = nvcl_id_list[0]
imagelog_data_list = reader.get_imagelog_data(nvcl_id)
```

**6. Call get_borehole_data() to get borehole data**

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
for ild in imagelog_data_list:
    if ild.log_type == LOG_TYPE and ild.log_name == ANALYSIS_CLASS:
        bh_data = reader.get_borehole_data(ild.log_id, HEIGHT_RESOLUTION, ANALYSIS_CLASS)
        # Print out the colour, mineral and class name at each depth
        for depth in bh_data:
            print("At ", depth, "my class, mineral, colour is", bh_data[depth].className,
                  bh_data[depth].classText, bh_data[depth].colour)
```

**7. Using the NVCL ids from Step 5, you can also call get_spectrallog_data() and get_profilometer_data()**

```python
spectrallog_data_list = reader.get_spectrallog_data(nvcl_id)
profilometer_data_list = reader.get_profilometer_data(nvcl_id)
```


