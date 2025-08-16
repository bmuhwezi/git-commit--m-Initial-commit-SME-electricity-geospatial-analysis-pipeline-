#!/usr/bin/env python3
"""
Roads feature extraction using Kenya roads data
"""

import sys
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, MultiLineString

from config import INPUT_PATHS, OUTPUT_PATHS, FEATURE_PARAMS
from utils.spatial_utils import create_point_buffer, split_dataframe, roads_to_multilines
from utils.file_utils import load_data, save_pickle


def load_roads_data():
    """Load roads shapefile data"""
    try:
        roads_gdf = gpd.read_file(INPUT_PATHS['roads_shapefile'])
        print(f"Loaded {len(roads_gdf)} road segments")
        return roads_gdf
    except Exception as e:
        print(f"Error loading roads data: {e}")
        raise


def calculate_distance_to_roads(lat, lon, roads_multiline):
    """Calculate distance from point to nearest road"""
    try:
        point = Point(lon, lat)
        distance = point.distance(roads_multiline)
        return distance
    except Exception as e:
        print(f"Error calculating distance to roads: {e}")
        return np.nan


def calculate_road_lengths_in_buffer(lat, lon, roads_gdf, buffer_meters=10000):
    """Calculate road lengths by class within buffer around point"""
    try:
        # Create buffer around point
        buffer_geom = create_point_buffer(lat, lon, buffer_meters)
        
        # Separate roads by class
        roads_class_a = roads_gdf[roads_gdf.ROADCLASS == 'A']
        roads_class_b = roads_gdf[roads_gdf.ROADCLASS == 'B']
        
        # Convert to multilines
        multiline_a = roads_to_multilines(roads_class_a)
        multiline_b = roads_to_multilines(roads_class_b)
        
        # Calculate intersections and lengths
        length_a = multiline_a.intersection(buffer_geom).length if not multiline_a.is_empty else 0
        length_b = multiline_b.intersection(buffer_geom).length if not multiline_b.is_empty else 0
        
        return {
            'road_class_A_length': length_a,
            'road_class_B_length': length_b,
            'total_road_length': length_a + length_b
        }
    except Exception as e:
        print(f"Error calculating road lengths in buffer: {e}")
        return {
            'road_class_A_length': 0,
            'road_class_B_length': 0,
            'total_road_length': 0
        }


def process_roads_distances_chunk(chunk_id):
    """Process road distance calculations for specific chunk"""
    # Load data
    a2_locs = load_data(INPUT_PATHS['a2_locations'])
    a2_bills = load_data(INPUT_PATHS['a2_bills'])
    roads_gdf = load_roads_data()
    
    # Create multiline from all roads for distance calculations
    roads_multiline = roads_to_multilines(roads_gdf)
    
    # Split data
    chunks = split_dataframe(a2_locs, FEATURE_PARAMS['num_chunks'])
    sc_locs = chunks[chunk_id].set_index('NIS_RAD')
    
    # Filter bills for this chunk
    chunk_bills = a2_bills[a2_bills.nis_rad.isin(sc_locs.index)]
    
    # Create results dataframe
    result = pd.DataFrame(index=chunk_bills.index)
    result['nis_rad'] = chunk_bills['nis_rad']
    
    # Calculate distances for each location
    distances = []
    for bill_idx, row in chunk_bills.iterrows():
        nis_rad = row['nis_rad']
        
        if nis_rad in sc_locs.index:
            lat, lon = sc_locs.loc[nis_rad, ['LAT', 'LON']]
            distance = calculate_distance_to_roads(lat, lon, roads_multiline)
            distances.append(distance)
        else:
            distances.append(np.nan)
    
    result['distance_to_road'] = distances
    
    # Save results
    output_path = f"{OUTPUT_PATHS['features_dir']}/roads/SC_road_distances_{chunk_id}.pck"
    save_pickle(result, output_path)
    print(f"Saved road distance features for chunk {chunk_id}")


def process_roads_lengths_chunk(chunk_id):
    """Process road length calculations for specific chunk"""
    # Load data
    a2_locs = load_data(INPUT_PATHS['a2_locations'])
    a2_bills = load_data(INPUT_PATHS['a2_bills'])
    roads_gdf = load_roads_data()
    
    # Split data
    chunks = split_dataframe(a2_locs, FEATURE_PARAMS['num_chunks'])
    sc_locs = chunks[chunk_id].set_index('NIS_RAD')
    
    # Filter bills for this chunk
    chunk_bills = a2_bills[a2_bills.nis_rad.isin(sc_locs.index)]
    
    # Create results dataframe
    result = pd.DataFrame(index=chunk_bills.index)
    result['nis_rad'] = chunk_bills['nis_rad']
    
    # Calculate road lengths for each location
    for bill_idx, row in chunk_bills.iterrows():
        nis_rad = row['nis_rad']
        
        if nis_rad in sc_locs.index:
            lat, lon = sc_locs.loc[nis_rad, ['LAT', 'LON']]
            road_lengths = calculate_road_lengths_in_buffer(
                lat, lon, roads_gdf, FEATURE_PARAMS['road_buffer_distance']
            )
            
            # Add road length features to result
            for key, value in road_lengths.items():
                result.loc[bill_idx, key] = value
        else:
            # Fill with NaN for missing locations
            result.loc[bill_idx, 'road_class_A_length'] = np.nan
            result.loc[bill_idx, 'road_class_B_length'] = np.nan
            result.loc[bill_idx, 'total_road_length'] = np.nan
    
    # Save results
    output_path = f"{OUTPUT_PATHS['features_dir']}/roads/SC_road_lengths_{chunk_id}.pck"
    save_pickle(result, output_path)
    print(f"Saved road length features for chunk {chunk_id}")


def process_chunk(chunk_id, feature_type='both'):
    """
    Process roads features for specific chunk
    
    Args:
        chunk_id: Chunk identifier for parallel processing
        feature_type: Type of features to extract ('distances', 'lengths', or 'both')
    """
    if feature_type in ['distances', 'both']:
        process_roads_distances_chunk(chunk_id)
    
    if feature_type in ['lengths', 'both']:
        process_roads_lengths_chunk(chunk_id)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python roads_extraction.py <chunk_id> [feature_type]")
        print("feature_type options: 'distances', 'lengths', 'both' (default)")
        sys.exit(1)
    
    chunk_id = int(sys.argv[1])
    feature_type = sys.argv[2] if len(sys.argv) > 2 else 'both'
    
    process_chunk(chunk_id, feature_type)