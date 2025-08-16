#!/usr/bin/env python3
"""
Population feature extraction using WorldPop data
"""

import sys
import pandas as pd
import numpy as np
import rasterio
from rasterio.mask import mask
import glob

from config import INPUT_PATHS, OUTPUT_PATHS, FEATURE_PARAMS
from utils.spatial_utils import create_point_buffer, split_dataframe
from utils.file_utils import load_data, save_pickle


def load_population_rasters():
    """Load population raster files"""
    files = sorted(glob.glob(INPUT_PATHS['worldpop_files']))
    rasters = {}
    
    for file in files:
        with rasterio.open(file) as src:
            # Extract year from filename
            year = int(file.split('_')[2])
            rasters[year] = src
    
    return rasters


def extract_population_in_buffer(lat, lon, raster, buffer_meters=500):
    """Extract population count within buffer around point"""
    buffer_geom = create_point_buffer(lat, lon, buffer_meters)
    
    try:
        masked_data = mask(raster, [buffer_geom], crop=True)[0]
        return np.sum(np.clip(masked_data, 0, np.inf))
    except:
        return 0


def process_chunk(chunk_id):
    """Process population extraction for specific chunk"""
    # Load data
    a2_locs = load_data(INPUT_PATHS['a2_locations'])
    a2_bills = load_data(INPUT_PATHS['a2_bills'])
    pop_rasters = load_population_rasters()
    
    # Split data
    chunks = split_dataframe(a2_locs, FEATURE_PARAMS['num_chunks'])
    sc_locs = chunks[chunk_id].set_index('NIS_RAD')
    
    # Filter bills for this chunk
    chunk_bills = a2_bills[a2_bills.nis_rad.isin(sc_locs.index)]
    
    # Create results dataframe
    result = pd.DataFrame(index=chunk_bills.index)
    result['nis_rad'] = chunk_bills['nis_rad']
    
    # Extract population for each year and location
    for bill_idx, row in chunk_bills.iterrows():
        nis_rad = row['nis_rad']
        
        if nis_rad in sc_locs.index:
            lat, lon = sc_locs.loc[nis_rad, ['LAT', 'LON']]
            
            # Get bill year
            if 'year' in row:
                bill_year = row['year']
            elif 'f_fact' in row:
                bill_year = pd.to_datetime(row['f_fact']).year
            else:
                bill_year = 2015  # default
            
            # Find closest population year
            available_years = list(pop_rasters.keys())
            closest_year = min(available_years, key=lambda x: abs(x - bill_year))
            
            # Extract population
            population = extract_population_in_buffer(
                lat, lon, pop_rasters[closest_year], FEATURE_PARAMS['buffer_radius']
            )
            result.loc[bill_idx, 'population'] = population
    
    # Save results
    output_path = f"{OUTPUT_PATHS['features_dir']}/population/SC_pop_{chunk_id}.pck"
    save_pickle(result, output_path)
    print(f"Saved population features for chunk {chunk_id}")


if __name__ == '__main__':
    chunk_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    process_chunk(chunk_id)
