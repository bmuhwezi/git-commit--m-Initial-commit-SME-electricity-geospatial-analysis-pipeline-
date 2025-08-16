#!/usr/bin/env python3
"""
Nighttime lights feature extraction using VIIRS data
"""

import sys
import pandas as pd
import numpy as np
import rasterio
from rasterio.mask import mask
import glob
from datetime import datetime

from config import INPUT_PATHS, OUTPUT_PATHS, FEATURE_PARAMS
from utils.spatial_utils import create_point_buffer, split_dataframe
from utils.file_utils import load_data, save_pickle


def load_viirs_rasters():
    """Load VIIRS nighttime lights raster files"""
    files = sorted(glob.glob(INPUT_PATHS['viirs_data']))
    rasters = {}
    
    for file in files:
        try:
            with rasterio.open(file) as src:
                # Extract year and month from filename
                # Assuming filename format contains date info (adjust as needed)
                filename = file.split('/')[-1]
                
                # Try different common VIIRS filename patterns
                if 'SVDNB' in filename:
                    # Format: SVDNB_npp_20150101-20151231_*.tif
                    year_part = filename.split('_')[2]
                    year = int(year_part[:4])
                elif len(filename.split('_')) > 2:
                    # Generic format with year in filename
                    parts = filename.split('_')
                    for part in parts:
                        if len(part) >= 4 and part[:4].isdigit():
                            year = int(part[:4])
                            break
                    else:
                        year = 2015  # default year
                else:
                    year = 2015  # default year
                
                rasters[year] = src
                
        except Exception as e:
            print(f"Warning: Could not load {file}: {e}")
            continue
    
    return rasters


def extract_nightlights_in_buffer(lat, lon, raster, buffer_meters=500):
    """Extract nighttime lights statistics within buffer around point"""
    buffer_geom = create_point_buffer(lat, lon, buffer_meters)
    
    try:
        masked_data, _ = mask(raster, [buffer_geom], crop=True)
        
        # Remove nodata values (typically negative values in VIIRS)
        valid_data = masked_data[masked_data >= 0]
        
        if len(valid_data) == 0:
            return {
                'lights_mean': 0,
                'lights_sum': 0,
                'lights_max': 0,
                'lights_std': 0,
                'lights_pixels': 0
            }
        
        return {
            'lights_mean': np.mean(valid_data),
            'lights_sum': np.sum(valid_data),
            'lights_max': np.max(valid_data),
            'lights_std': np.std(valid_data),
            'lights_pixels': len(valid_data)
        }
        
    except Exception as e:
        print(f"Error extracting nightlights: {e}")
        return {
            'lights_mean': 0,
            'lights_sum': 0,
            'lights_max': 0,
            'lights_std': 0,
            'lights_pixels': 0
        }


def get_bill_year(row):
    """Extract year from bill data"""
    if 'year' in row:
        return row['year']
    elif 'f_fact' in row:
        return pd.to_datetime(row['f_fact']).year
    elif 'date' in row:
        return pd.to_datetime(row['date']).year
    else:
        return 2015  # default year


def find_closest_raster_year(target_year, available_years):
    """Find the closest available raster year to target year"""
    if not available_years:
        return None
    return min(available_years, key=lambda x: abs(x - target_year))


def process_chunk(chunk_id):
    """Process nighttime lights extraction for specific chunk"""
    print(f"Processing nighttime lights for chunk {chunk_id}")
    
    # Load data
    a2_locs = load_data(INPUT_PATHS['a2_locations'])
    a2_bills = load_data(INPUT_PATHS['a2_bills'])
    viirs_rasters = load_viirs_rasters()
    
    if not viirs_rasters:
        print("Warning: No VIIRS rasters found")
        return
    
    print(f"Loaded {len(viirs_rasters)} VIIRS rasters for years: {list(viirs_rasters.keys())}")
    
    # Split data into chunks
    chunks = split_dataframe(a2_locs, FEATURE_PARAMS['num_chunks'])
    sc_locs = chunks[chunk_id].set_index('NIS_RAD')
    
    # Filter bills for this chunk
    chunk_bills = a2_bills[a2_bills.nis_rad.isin(sc_locs.index)]
    
    print(f"Processing {len(chunk_bills)} bills for {len(sc_locs)} locations")
    
    # Create results dataframe
    result = pd.DataFrame(index=chunk_bills.index)
    result['nis_rad'] = chunk_bills['nis_rad']
    
    # Initialize nightlights columns
    lights_columns = ['lights_mean', 'lights_sum', 'lights_max', 'lights_std', 'lights_pixels']
    for col in lights_columns:
        result[col] = 0.0
    
    # Process each bill
    processed_count = 0
    for bill_idx, row in chunk_bills.iterrows():
        nis_rad = row['nis_rad']
        
        if nis_rad in sc_locs.index:
            lat, lon = sc_locs.loc[nis_rad, ['LAT', 'LON']]
            
            # Get bill year
            bill_year = get_bill_year(row)
            
            # Find closest raster year
            available_years = list(viirs_rasters.keys())
            closest_year = find_closest_raster_year(bill_year, available_years)
            
            if closest_year is not None:
                # Extract nighttime lights statistics
                lights_stats = extract_nightlights_in_buffer(
                    lat, lon, viirs_rasters[closest_year], FEATURE_PARAMS['buffer_radius']
                )
                
                # Store results
                for stat_name, value in lights_stats.items():
                    result.loc[bill_idx, stat_name] = value
            
            processed_count += 1
            if processed_count % 1000 == 0:
                print(f"Processed {processed_count}/{len(chunk_bills)} bills")
    
    # Save results
    output_path = f"{OUTPUT_PATHS['features_dir']}/nightlights/SC_nightlights_{chunk_id}.pck"
    save_pickle(result, output_path)
    print(f"Saved nighttime lights features for chunk {chunk_id} to {output_path}")
    
    return result


def combine_nightlights_results():
    """Combine all nightlights chunk results into single file"""
    from utils.file_utils import combine_chunk_results
    
    print("Combining nighttime lights results...")
    combined_result = combine_chunk_results(
        base_path=f"{OUTPUT_PATHS['features_dir']}/nightlights/SC_nightlights_",
        num_chunks=FEATURE_PARAMS['num_chunks'],
        output_filename=f"{OUTPUT_PATHS['features_dir']}/nightlights/SC_nightlights_combined.pck"
    )
    
    if combined_result is not None:
        print(f"Combined nightlights features: {combined_result.shape}")
        print("Nightlights feature statistics:")
        print(combined_result[['lights_mean', 'lights_sum', 'lights_max']].describe())
    
    return combined_result


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'combine':
            # Combine all chunk results
            combine_nightlights_results()
        else:
            # Process specific chunk
            chunk_id = int(sys.argv[1])
            process_chunk(chunk_id)
    else:
        # Process chunk 0 by default
        process_chunk(0)