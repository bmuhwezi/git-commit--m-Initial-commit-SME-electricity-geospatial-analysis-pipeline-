#!/usr/bin/env python3
"""
Financial Service Provider (FSP) feature extraction
"""

import sys
import pandas as pd
import geopandas as gpd
import numpy as np
from rtree import index

from config import INPUT_PATHS, OUTPUT_PATHS, FEATURE_PARAMS
from utils.spatial_utils import get_radius_degrees, split_dataframe
from utils.file_utils import load_data, save_pickle


def load_fsp_data():
    """Load FSP shapefile data"""
    fsp = gpd.read_file(INPUT_PATHS['fsp_shapefile'])
    fsp.rename(columns={'GPSLatitud': 'Lat', 'GPSLongitu': 'Lon'}, inplace=True)
    
    # Process dates
    valid_year_idx = fsp[fsp.year > 0].index
    fsp.loc[valid_year_idx, 'start_dte'] = pd.to_datetime(
        fsp.loc[valid_year_idx, ['year', 'month', 'day']]
    )
    fsp.loc[fsp.year == 0, 'start_dte'] = fsp.start_dte.min()
    
    return fsp


def create_spatial_index(df):
    """Create spatial index for points"""
    idx = index.Index()
    for i in df.index:
        x, y = df['Lon'][i], df['Lat'][i]
        idx.insert(i, (x, y))
    return idx


def find_fsp_in_buffer(sc_locs, fsp_data, buffer_meters=500):
    """Find FSP points within buffer of each SC location"""
    radius = get_radius_degrees(buffer_meters)
    
    results = {}
    for fsp_type, fsp_group in fsp_data.groupby('factype'):
        idx = create_spatial_index(fsp_group)
        
        for sc_idx in sc_locs.index:
            x, y = sc_locs['LON'][sc_idx], sc_locs['LAT'][sc_idx]
            buffer_bounds = (x-radius, y-radius, x+radius, y+radius)
            
            hits_idx = list(idx.intersection(buffer_bounds))
            hits = fsp_group.loc[hits_idx]
            
            # Filter to actual buffer distance
            actual_hits = []
            for hit_idx in hits_idx:
                hit_x, hit_y = fsp_group.loc[hit_idx, ['Lon', 'Lat']]
                distance = np.sqrt((x - hit_x)**2 + (y - hit_y)**2)
                if distance <= radius:
                    actual_hits.append(hit_idx)
            
            if sc_idx not in results:
                results[sc_idx] = {}
            results[sc_idx][fsp_type] = len(actual_hits)
    
    return results


def process_chunk(chunk_id):
    """Process FSP extraction for specific chunk"""
    # Load data
    a2_locs = load_data(INPUT_PATHS['a2_locations'])
    a2_bills = load_data(INPUT_PATHS['a2_bills'])
    fsp_data = load_fsp_data()
    
    # Split data
    chunks = split_dataframe(a2_locs, FEATURE_PARAMS['num_chunks'])
    sc_locs = chunks[chunk_id].set_index('NIS_RAD')
    
    # Filter bills for this chunk
    chunk_bills = a2_bills[a2_bills.nis_rad.isin(sc_locs.index)]
    
    # Find FSPs in buffer
    fsp_counts = find_fsp_in_buffer(sc_locs, fsp_data, FEATURE_PARAMS['buffer_radius'])
    
    # Create results dataframe
    result = pd.DataFrame(index=chunk_bills.index)
    result['nis_rad'] = chunk_bills['nis_rad']
    
    for bill_idx, row in chunk_bills.iterrows():
        nis_rad = row['nis_rad']
        if nis_rad in fsp_counts:
            for fsp_type, count in fsp_counts[nis_rad].items():
                result.loc[bill_idx, fsp_type] = count
    
    # Save results
    output_path = f"{OUTPUT_PATHS['features_dir']}/fsp/Nof_FSP_{chunk_id}.pck"
    save_pickle(result, output_path)
    print(f"Saved FSP features for chunk {chunk_id}")


if __name__ == '__main__':
    chunk_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    process_chunk(chunk_id)
