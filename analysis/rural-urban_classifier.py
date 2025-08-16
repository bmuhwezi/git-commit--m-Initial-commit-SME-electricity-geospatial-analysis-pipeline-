

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Geographic classification utilities for service connections
"""

import pandas as pd
import numpy as np


def compute_pixel_coordinates(lat, lon):
    """
    Convert lat/lon coordinates to pixel coordinates
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
        
    Returns:
        tuple: (x, y) pixel coordinates
    """
    pixel_width = 0.008333
    pixel_height = 0.008340186677631579
    extent = [33.91261, 41.91261, -4.670972, 5.470695]
    x_origin = extent[0]
    y_origin = extent[3]
    
    x = int(np.floor(abs(x_origin - lon) / pixel_width))
    y = int(np.floor(abs(y_origin - lat) / pixel_height))
    
    # Boundary checks
    if y == 1216:
        y = 1215
    if x == 960:
        x = 959
        
    return x, y


def classify_locations(location_data, rural_urban_raster):
    """
    Classify service connections as Rural, Urban, or Peri-Urban
    
    Args:
        location_data (pd.DataFrame): DataFrame with LAT, LON columns
        rural_urban_raster (pd.DataFrame): Rural/urban classification raster data
        
    Returns:
        pd.DataFrame: Location data with classification column
    """
    # Filter out locations without coordinates
    data = location_data[~location_data[['LAT', 'LON']].isna().any(1)].copy()
    
    # Convert raster to numpy array
    raster_array = rural_urban_raster.to_numpy()
    
    # Calculate pixel coordinates for each location
    pixel_coords = []
    for i in data.index:
        x, y = compute_pixel_coordinates(data.LAT.loc[i], data.LON.loc[i])
        pixel_coords.append((x, y))
    
    # Extract pixel coordinates
    data['X'] = [coord[0] for coord in pixel_coords]
    data['Y'] = [coord[1] for coord in pixel_coords]
    
    # Get pixel values and classify
    data['pixel_value'] = raster_array[data['Y'].values, data['X'].values]
    
    # Apply classification based on pixel values
    data.loc[data['pixel_value'] == float('-inf'), 'classification'] = 'NA'
    data.loc[data['pixel_value'] == 0, 'classification'] = 'Peri_Urban'
    data.loc[data['pixel_value'] == 50, 'classification'] = 'Urban'
    data.loc[data['pixel_value'] == 100, 'classification'] = 'Rural'
    
    return data


def create_binary_rural_urban(classified_data):
    """
    Create binary rural/urban classification
    
    Args:
        classified_data (pd.DataFrame): Data with 'classification' column
        
    Returns:
        pd.Series: Binary rural/urban classification
    """
    binary_classification = pd.Series(index=classified_data.index)
    rural_mask = classified_data['classification'] == 'Rural'
    
    binary_classification[rural_mask] = 'Rural'
    binary_classification[~rural_mask] = 'Urban'
    
    return binary_classification