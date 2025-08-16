#!/usr/bin/env python3

# Input data paths
INPUT_PATHS = {
    'a2_locations': '/home/bmuhwezi/Research/Domestic_consumers/sjob_Array/A1locs.pck',
    'a2_bills': '/home/jtaneja/work/projects/smallcommercial/SC_NL/data_folder/A1_bills.csv',
    'customers_all': '/home/bmuhwezi/Research/Domestic_consumers/DomesticHH.pck',
    'tx_data': '/home/jtaneja/work/code/FDB/TXdatafull4.pck',
    
    # Geospatial data
    'fsp_shapefile': '/home/jtaneja/work/projects/smallcommercial/SC_FSP/finaccess/finaccess.shp',
    'roads_shapefile': '/home/jtaneja/work/projects/smallcommercial/Roads/kenya_roads/Kenya_Roads.shp',
    'county_shapefile': '/home/jtaneja/work/projects/smallcommercial/Energy4growth/County/County.shp',
    'wards_shapefile': '/home/jtaneja/work/projects/smallcommercial/Energy4growth/kenya_wards/Kenya wards.shp',
    'constituency_shapefile': '/home/jtaneja/work/projects/smallcommercial/Data/ken_adm_iebc_20191031_shp/ken_admbnda_adm2_iebc_20191031.shp',
    
    # Raster data
    'worldpop_files': '/home/jtaneja/work/projects/worldpop/data/KEN/*',
    'viirs_data': '/home/jtaneja/scratch/data/VIIRS/*.tif',  # Updated pattern
    'viirs_monthly': '/home/jtaneja/scratch/data/VIIRS/monthly/*.tif',  # Monthly composites
    'viirs_annual': '/home/jtaneja/scratch/data/VIIRS/annual/*.tif',    # Annual composites
    'structures': '/home/jtaneja/work/data/structLocs/structLocs.pck'
}

# Output paths
OUTPUT_PATHS = {
    'base_dir': './outputs',
    'features_dir': './outputs/features',
    'plots_dir': './outputs/plots',
    'results_dir': './outputs/results',
    'final_dataset': './outputs/DF_features.csv'
}

# Feature extraction parameters
FEATURE_PARAMS = {
    'buffer_radius': 500,  # meters
    'num_chunks': 36,      # for parallel processing
    'quantile_threshold': 0.95,
    'road_buffer_distance': 10000,  # meters
    
    # Nightlights-specific parameters
    'nightlights_buffer_sizes': [250, 500, 1000],  # multiple buffer sizes
    'nightlights_nodata_threshold': -999,          # values below this are considered nodata
    'nightlights_max_valid': 1000,                 # maximum reasonable nightlights value
    
    # Population-specific parameters
    'population_buffer_sizes': [250, 500, 1000],   # multiple buffer sizes for population too
}

# Data quality parameters
DATA_QUALITY = {
    'min_lat': -5.0,     # Kenya bounds
    'max_lat': 5.5,
    'min_lon': 33.5,
    'max_lon': 42.0,
    'max_reasonable_population': 50000,  # per 500m buffer
    'max_reasonable_nightlights': 1000   # typical max for urban areas
}

# SLURM configuration
#SLURM_CONFIG = {
#    'email': 'bmuhwezi@umass.edu',
#    'cpus_per_task': 12,
#    'mem_per_cpu': 10000,
#    'partition_long': 'longq',
#    'partition_def': 'defq',
#    'time_limit': '08:00:00'
#}