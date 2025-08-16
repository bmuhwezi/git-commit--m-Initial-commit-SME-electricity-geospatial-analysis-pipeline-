#!/usr/bin/env python3
"""
Electrified Structures feature extraction
"""

import sys
import pandas as pd
import numpy as np
from rtree import index
from shapely.geometry import Point

from config import INPUT_PATHS, OUTPUT_PATHS, FEATURE_PARAMS
from utils.spatial_utils import get_radius_degrees, split_dataframe
from utils.file_utils import load_data, save_pickle


def create_customer_spatial_index(customers_df):
    """Create spatial index for customer locations"""
    idx = index.Index()
    
    # Filter valid customers with non-null coordinates and installation dates
    valid_customers = customers_df[
        ~customers_df[['LAT', 'LON', 'installation']].isna().any(axis=1)
    ].copy()
    
    # Build spatial index
    for i in valid_customers.index:
        lat, lon = valid_customers.loc[i, ['LAT', 'LON']]
        idx.insert(i, (lat, lon, lat, lon))  # (minx, miny, maxx, maxy)
    
    return idx, valid_customers


def count_electrified_structures(tx_data, customers_in_buffer):
    """
    Count unique electrified structures within buffer
    
    Args:
        tx_data: DataFrame with transformer locations
        customers_in_buffer: DataFrame with customers in buffer area
        
    Returns:
        Total count of unique electrified structures
    """
    if len(customers_in_buffer) == 0:
        return 0
    
    # Count transformer locations
    tx_matches = pd.merge(
        customers_in_buffer.reset_index(), 
        tx_data[['LAT', 'LON']], 
        on=['LAT', 'LON'],
        how='inner'
    )
    tx_count = len(tx_matches)
    
    # Count non-transformer locations (unique by coordinates)
    non_tx_customers = customers_in_buffer[
        ~customers_in_buffer.index.isin(tx_data.index)
    ]
    non_tx_count = non_tx_customers.drop_duplicates(subset=['LAT', 'LON']).shape[0]
    
    return tx_count + non_tx_count


def find_customers_in_buffer(center_lat, center_lon, spatial_index, valid_customers, 
                           buffer_meters, max_period=None):
    """
    Find customers within buffer of center point
    
    Args:
        center_lat, center_lon: Center coordinates
        spatial_index: rtree spatial index
        valid_customers: DataFrame with customer data
        buffer_meters: Buffer radius in meters
        max_period: Maximum installation period to consider
        
    Returns:
        DataFrame with customers in buffer, filtered by installation period
    """
    radius_deg = get_radius_degrees(buffer_meters)
    buffer_geom = Point(center_lon, center_lat).buffer(radius_deg)
    
    # Query spatial index for potential matches
    buffer_bounds = buffer_geom.bounds
    potential_hits = list(spatial_index.intersection(buffer_bounds))
    
    if not potential_hits:
        return pd.DataFrame()
    
    # Get potential customers
    potential_customers = valid_customers.loc[potential_hits].copy()
    
    # Filter to actual buffer using precise geometry
    in_buffer_mask = potential_customers.apply(
        lambda row: buffer_geom.contains(Point(row['LON'], row['LAT'])), 
        axis=1
    )
    customers_in_buffer = potential_customers[in_buffer_mask]
    
    # Filter by installation period if specified
    if max_period is not None:
        customers_in_buffer = customers_in_buffer[
            customers_in_buffer['installation'] <= max_period
        ]
    
    return customers_in_buffer


def process_chunk(chunk_id):
    """Process electrified structures extraction for specific chunk"""
    print(f"Processing electrified structures for chunk {chunk_id}")
    
    # Load data
    a2_locs = load_data(INPUT_PATHS['a2_locations'])
    a2_bills = load_data(INPUT_PATHS['a2_bills'])
    customers_all = load_data(INPUT_PATHS['customers_all'])
    tx_data = load_data(INPUT_PATHS['tx_data'])
    
    # Process installation dates
    customers_all['installation'] = pd.to_datetime(
        customers_all['installation'], 
        dayfirst=True, 
        errors='coerce'
    ).dt.to_period('M')
    
    # Process bills period
    a2_bills['period'] = pd.to_datetime(a2_bills['period']).dt.to_period('M')
    
    # Split locations data
    chunks = split_dataframe(a2_locs, FEATURE_PARAMS['num_chunks'])
    sc_locs = chunks[chunk_id].set_index('NIS_RAD')
    
    # Filter bills for this chunk
    chunk_bills = a2_bills[a2_bills.nis_rad.isin(sc_locs.index)].copy()
    
    if len(chunk_bills) == 0:
        print(f"No bills found for chunk {chunk_id}")
        return
    
    # Create spatial index for customers
    spatial_idx, valid_customers = create_customer_spatial_index(customers_all)
    
    # Initialize results
    results = pd.DataFrame(index=chunk_bills.index)
    results['nis_rad'] = chunk_bills['nis_rad']
    results['period'] = chunk_bills['period']
    results['electrified_structures'] = 0
    
    # Process each bill record
    print(f"Processing {len(chunk_bills)} bill records...")
    
    for bill_idx, bill_row in chunk_bills.iterrows():
        nis_rad = bill_row['nis_rad']
        bill_period = bill_row['period']
        
        # Get customer location for this NIS_RAD
        customer_loc = customers_all[customers_all.NIS_RAD == nis_rad]
        
        if len(customer_loc) == 0:
            continue
            
        # Use first match if multiple customers with same NIS_RAD
        customer_loc = customer_loc.iloc[0]
        center_lat, center_lon = customer_loc['LAT'], customer_loc['LON']
        
        # Skip if coordinates are invalid
        if pd.isna(center_lat) or pd.isna(center_lon):
            continue
        
        # Find customers in buffer, installed before or during bill period
        customers_in_buffer = find_customers_in_buffer(
            center_lat, center_lon, spatial_idx, valid_customers,
            FEATURE_PARAMS['buffer_radius'], max_period=bill_period
        )
        
        # Count electrified structures
        struct_count = count_electrified_structures(tx_data, customers_in_buffer)
        results.loc[bill_idx, 'electrified_structures'] = struct_count
    
    # Save results
    output_path = f"{OUTPUT_PATHS['features_dir']}/structures/electrified_structures_{chunk_id}.pck"
    save_pickle(results, output_path)
    print(f"Saved electrified structures features for chunk {chunk_id} to {output_path}")


if __name__ == '__main__':
    chunk_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    process_chunk(chunk_id)