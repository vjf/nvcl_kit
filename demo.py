#!/usr/bin/env python3
from nvcl_kit.reader import NVCLReader
from types import SimpleNamespace
import sys

#
# A very rough script to demonstrate 'nvcl_kit'
#


# Provider list. Format is (WFS service URL, NVCL service URL, bounding box coords)
prov_list = [ ("http://www.mrt.tas.gov.au:80/web-services/ows", "http://www.mrt.tas.gov.au/NVCLDataServices/", { "west": 143.75, "south": -43.75, "east": 148.75, "north": -39.75 }),
              ("http://geology.data.vic.gov.au/nvcl/ows", "http://geology.data.vic.gov.au/NVCLDataServices", None),
              ("https://gs.geoscience.nsw.gov.au/geoserver/ows", "https://nvcl.geoscience.nsw.gov.au/NVCLDataServices", None),
              ("https://geology.information.qld.gov.au/geoserver/ows", "https://geology.information.qld.gov.au/NVCLDataServices", None),
              ("http://geology.data.nt.gov.au:80/geoserver/ows", "http://geology.data.nt.gov.au:80/NVCLDataServices", None),
              ("https://sarigdata.pir.sa.gov.au/geoserver/ows", "https://sarigdata.pir.sa.gov.au/nvcl/NVCLDataServices",None),
              ("http://geossdi.dmp.wa.gov.au/services/ows",  "http://geossdi.dmp.wa.gov.au/NVCLDataServices", None) ]


def do_demo(wfs, nvcl, bbox):
    print("\n\n\n", wfs.upper())
    param = SimpleNamespace()
    param.WFS_URL = wfs
    param.NVCL_URL = nvcl
    if bbox:
        param.BBOX= bbox
    param.MAX_BOREHOLES = 20
    reader = NVCLReader(param)

    if not reader.wfs:
        print("ERROR!", wfs, nvcl)

    bh_list = reader.get_boreholes_list()
    print("bh_list = ", bh_list[:5])

    nvcl_id_list = reader.get_nvcl_id_list()
    print("nvcl_id_list = ", nvcl_id_list[:5])

    # Get list of NVCL ids
    nvcl_id_list = reader.get_nvcl_id_list()
    # Get NVCL log id for first borehole in list
    if not nvcl_id_list:
        print("!!!! No NVCL ids for", nvcl)
        return
    nvcl_id = nvcl_id_list[0]
    imagelog_data_list = reader.get_imagelog_data(nvcl_id)
    for ild in imagelog_data_list[:10]:
        print(ild.log_id,
              ild.log_name,
              ild.log_type,
              ild.algorithmout_id)

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
    for ild in imagelog_data_list[:10]:
        if ild.log_type == LOG_TYPE and ild.log_name == ANALYSIS_CLASS:
            bh_data = reader.get_borehole_data(ild.log_id, HEIGHT_RESOLUTION, ANALYSIS_CLASS)
            print('get_borehole_data()')
            # Print out the colour, mineral and class name at each depth
            for depth in bh_data:
                print("At ", depth, "my class, mineral, colour is", bh_data[depth].className,
                      bh_data[depth].classText, bh_data[depth].colour)

    print('get_spectrallog_data()')
    spectrallog_data_list = reader.get_spectrallog_data(nvcl_id)
    for sld in spectrallog_data_list[:4]:
        print(sld.log_id,
              sld.log_name,
              sld.wavelength_units,
              sld.sample_count,
              sld.script,
              sld.script_raw,
              sld.wavelengths)

    print('get_profilometer_data()')
    profilometer_data_list = reader.get_profilometer_data(nvcl_id)
    for pdl in profilometer_data_list[:10]:
        print(pdl.log_id,
              pdl.log_name,
              pdl.max_val,
              pdl.min_val,
              pdl.floats_per_sample,
              pdl.sample_count)

    print('get_dataset_list()')
    dataset_list = reader.get_dataset_list(nvcl_id)
    for dataset in dataset_list[:10]:
        print(dataset.dataset_id,
              dataset.dataset_name,
              dataset.borehole_uri,
              dataset.tray_id,
              dataset.section_id,
              dataset.domain_id)

    print('get_datasetid_list()')
    datasetid_list = reader.get_datasetid_list(nvcl_id)
    for dataset_id in datasetid_list[:5]:
        print('dataset_id:', dataset_id)

        # GET_MOSAIC_IMGLOGS, GET_MOSAIC_IMAGE
        img_log_list = reader.get_mosaic_imglogs(dataset_id)
        print('get_mosaic_imglogs() ', img_log_list)
        for img_log in img_log_list[:10]:
            print(img_log.log_id,
                  img_log.log_name,
                  img_log.sample_count)
            html = reader.get_mosaic_image(img_log.log_id)
            print('get_mosaic_image()', html[:400])


        # GET_TRAY_THUMBNAIL_IMGLOGS, GET_TRAY_THUMB_HTML, GET_TRAY_THUMB_JPG
        # & GET_TRAY_DEPTHS
        print('get_tray_thumb_imglogs()')
        img_log_list = reader.get_tray_thumb_imglogs(dataset_id)
        for img_log in img_log_list[:10]:
            print(img_log.log_id,
                  img_log.log_name,
                  img_log.sample_count)
            html = reader.get_tray_thumb_html(dataset_id, img_log.log_id)
            print('get_tray_thumb_html()', html[:400])
            jpg = reader.get_tray_thumb_jpg(img_log.log_id)
            print('get_tray_thumb_jpg()', repr(jpg)[:100])
            depth_list = reader.get_tray_depths(img_log.log_id)
            print('get_tray_depths():')
            for depth in depth_list[:10]:
                print(depth.sample_no,
                      depth.start_value,
                      depth.end_value)


        # GET_TRAY_IMGLOGS, GET_TRAY_THUMB_HTML & GET_TRAY_DEPTHS
        print('get_tray_imglogs()')
        img_log_list = reader.get_tray_imglogs(dataset_id)
        for img_log in img_log_list[:10]:
            print(img_log.log_id,
                  img_log.log_name,
                  img_log.sample_count)
            html = reader.get_tray_thumb_html(dataset_id, img_log.log_id)
            print('get_tray_thumb_html()', html[:400])
            depth_list = reader.get_tray_depths(img_log.log_id)
            print('get_tray_depths():')
            for depth in depth_list[:10]:
                print(depth.sample_no,
                      depth.start_value,
                      depth.end_value)


        # GET_IMAGERY_IMGLOGS
        print('get_imagery_imglogs()')
        img_log_list = reader.get_imagery_imglogs(dataset_id)
        for img_log in img_log_list[:10]:
            print(img_log.log_id,
                  img_log.log_name,
                  img_log.sample_count)
            print('get_imagery_logs()', html[:400])


        # GET_SCALAR_LOGS & PLOT_SCALAR_PNG
        print('get_scalar_logs()')
        scalar_log_list = reader.get_scalar_logs(dataset_id)
        for scalar_log in scalar_log_list[:10]:
            print(scalar_log.log_id,
                  scalar_log.log_name)
            png = reader.plot_scalar_png(scalar_log.log_id)
            print('plot_scalar_png()', repr(png)[:100])


        # PLOT_SCALARS_HTML
        log_id_list = [scalar_log.log_id for scalar_log in scalar_log_list]
        html = reader.plot_scalars_html(log_id_list)
        print('plot_scalars_html()', html[:400])


        # GET_SCALAR_LOGS & GET_SCALAR_DATA
        sca_log_list = reader.get_scalar_logs(dataset_id)
        print('get_scalar_logs()', sca_log_list[:10])
        log_id_list = [sca_log.log_id for sca_log in sca_log_list][:4]
        csv = reader.get_scalar_data(log_id_list)
        print('get_scalar_data()', csv[:400])


        # GET_SAMPLED_SCALAR_DATA
        for sca_log in sca_log_list[:5]:
            sampled_data = reader.get_sampled_scalar_data(sca_log.log_id,
                                                     outputformat='json',
                                                     startdepth=0,
                                                     enddepth=2000,
                                                     interval=100)
            print('get_sampled_scalar_data()', sampled_data[:400])


#
# MAIN PART OF SCRIPT
#
if __name__ == "__main__":

    # Loop over all the providers
    for wfs, nvcl, bbox in prov_list:
        do_demo(wfs, nvcl, bbox)

