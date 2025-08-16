#!/usr/bin/env python3
"""
Common spatial calculation utilities
"""

import numpy as np
import pandas as pd
from shapely.geometry import Point, LineString, MultiLineString
import rasterio
from rasterio.mask import mask


def get_radius_degrees(buffer_meters):
    """Convert buffer distance in meters to degrees"""
    lat_degree = 110.54 * 1000  # meters per degree latitude
    lon_degree = 111.32 * 1000  # meters per degree longitude
    lat_radius = buffer_meters / lat_degree
    lon_radius = buffer_meters / lon_degree
    return max(lat_radius, lon_radius)


def create_point_buffer(lat, lon, radius_meters):
    """Create buffer around point"""
    radius_degrees = get_radius_degrees(radius_meters)
    return Point(lon, lat).buffer(radius_degrees)


def split_dataframe(df, num_chunks):
    """Split dataframe into chunks for parallel processing"""
    return np.array_split(df.reset_index(), num_chunks)


def roads_to_multilines(roads_gdf):
    """
    Convert roads GeoDataFrame to single MultiLineString
    
    Args:
        roads_gdf: GeoDataFrame containing road geometries
        
    Returns:
        MultiLineString combining all road segments
    """
    lines = []
    
    for geom in roads_gdf.geometry:
        if geom is None:
            continue
        elif geom.geom_type == 'LineString':
            lines.append(geom)
        elif geom.geom_type == 'MultiLineString':
            lines.extend(list(geom.geoms))
    
    return MultiLineString(lines) if lines else MultiLineString([])


def calculate_point_to_geometry_distance(point, geometry):
    """
    Calculate distance between a point and any geometry
    
    Args:
        point: Shapely Point object
        geometry: Shapely geometry object
        
    Returns:
        Distance in coordinate units
    """
    try:
        return point.distance(geometry)
    except Exception as e:
        print(f"Error calculating distance: {e}")
        return np.inf


def extract_raster_stats_in_buffer(lat, lon, raster, buffer_meters, 
                                   nodata_threshold=-999, max_valid_value=None):
    """
    Extract comprehensive raster statistics within buffer around point
    
    Args:
        lat, lon: Point coordinates
        raster: Open rasterio dataset
        buffer_meters: Buffer radius in meters
        nodata_threshold: Values below this are considered nodata
        max_valid_value: Values above this are considered invalid
        
    Returns:
        Dictionary with statistical measures
    """
    buffer_geom = create_point_buffer(lat, lon, buffer_meters)
    
    try:
        masked_data, _ = mask(raster, [buffer_geom], crop=True)
        
        # Remove nodata and invalid values
        valid_mask = masked_data >= nodata_threshold
        if max_valid_value is not None:
            valid_mask &= (masked_data <= max_valid_value)
        
        valid_data = masked_data[valid_mask]
        
        if len(valid_data) == 0:
            return {
                'mean': 0,
                'sum': 0,
                'max': 0,
                'min': 0,
                'std': 0,
                'median': 0,
                'pixels_count': 0,
                'pixels_nonzero': 0
            }
        
        return {
            'mean': float(np.mean(valid_data)),
            'sum': float(np.sum(valid_data)),
            'max': float(np.max(valid_data)),
            'min': float(np.min(valid_data)),
            'std': float(np.std(valid_data)),
            'median': float(np.median(valid_data)),
            'pixels_count': int(len(valid_data)),
            'pixels_nonzero': int(np.sum(valid_data > 0))
        }
        
    except Exception as e:
        print(f"Error extracting raster stats: {e}")
        return {
            'mean': 0, 'sum': 0, 'max': 0, 'min': 0, 'std': 0, 
            'median': 0, 'pixels_count': 0, 'pixels_nonzero': 0
        }


def validate_coordinates(lat, lon, bounds=None):
    """
    Validate coordinate values
    
    Args:
        lat, lon: Coordinates to validate
        bounds: Dictionary with min_lat, max_lat, min_lon, max_lon
        
    Returns:
        Boolean indicating if coordinates are valid
    """
    # Basic validation
    if pd.isna(lat) or pd.isna(lon):
        return False
    
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return False
    
    # Bounds validation if provided
    if bounds:
        if not (bounds.get('min_lat', -90) <= lat <= bounds.get('max_lat', 90)):
            return False
        if not (bounds.get('min_lon', -180) <= lon <= bounds.get('max_lon', 180)):
            return False
    
    return True


def create_multiple_buffers(lat, lon, buffer_sizes):
    """
    Create multiple buffer sizes around a point
    
    Args:
        lat, lon: Point coordinates
        buffer_sizes: List of buffer radii in meters
        
    Returns:
        Dictionary mapping buffer size to buffer geometry
    """
    buffers = {}
    for size in buffer_sizes:
        try:
            buffers[size] = create_point_buffer(lat, lon, size)
        except Exception as e:
            print(f"Error creating buffer of size {size}: {e}")
            buffers[size] = None
    
    return buffers




def calculate_raster_statistics_multi_buffer(lat, lon, raster, buffer_sizes, 
                                           prefix="", **kwargs):
    """
    Calculate raster statistics for multiple buffer sizes
    
    Args:
        lat, lon: Point coordinates
        raster: Open rasterio dataset
        buffer_sizes: List of buffer radii in meters
        prefix: Prefix for column names
        **kwargs: Additional arguments for extract_raster_stats_in_buffer
        
    Returns:
        Dictionary with statistics for each buffer size
    """
    all_stats = {}
    
    for buffer_size in buffer_sizes:
        stats = extract_raster_stats_in_buffer(lat, lon, raster, buffer_size, **kwargs)
        
        # Add buffer size to column names
        for stat_name, value in stats.items():
            col_name = f"{prefix}{stat_name}_{buffer_size}m" if prefix else f"{stat_name}_{buffer_size}m"
            all_stats[col_name] = value
    
    return all_stats


def create_spatial_index_from_dataframe(df, lat_col='LAT', lon_col='LON', 
                                       filter_valid=True):
    """
    Create rtree spatial index from DataFrame
    
    Args:
        df: DataFrame with coordinate columns
        lat_col: Name of latitude column
        lon_col: Name of longitude column
        filter_valid: Whether to filter out invalid coordinates
        
    Returns:
        Tuple of (spatial_index, valid_dataframe)
    """
    from rtree import index
    
    idx = index.Index()
    
    if filter_valid:
        # Filter out rows with invalid coordinates
        valid_mask = (
            df[lat_col].notna() & 
            df[lon_col].notna() & 
            (df[lat_col] >= -90) & (df[lat_col] <= 90) &
            (df[lon_col] >= -180) & (df[lon_col] <= 180)
        )
        valid_df = df[valid_mask].copy()
    else:
        valid_df = df.copy()
    
    # Build spatial index
    for i in valid_df.index:
        lat, lon = valid_df.loc[i, [lat_col, lon_col]]
        idx.insert(i, (lon, lat, lon, lat))  # (minx, miny, maxx, maxy)
    
    return idx, valid_df


def query_spatial_index_with_buffer(spatial_index, center_lat, center_lon, 
                                  buffer_meters, valid_df, 
                                  lat_col='LAT', lon_col='LON'):
    """
    Query spatial index for points within buffer
    
    Args:
        spatial_index: rtree Index object
        center_lat, center_lon: Center coordinates
        buffer_meters: Buffer radius in meters
        valid_df: DataFrame with valid coordinates
        lat_col: Name of latitude column
        lon_col: Name of longitude column
        
    Returns:
        DataFrame with points within buffer
    """
    radius_deg = get_radius_degrees(buffer_meters)
    buffer_geom = Point(center_lon, center_lat).buffer(radius_deg)
    
    # Query spatial index for potential matches
    buffer_bounds = buffer_geom.bounds
    potential_hits = list(spatial_index.intersection(buffer_bounds))
    
    if not potential_hits:
        return valid_df.iloc[0:0].copy()  # Return empty DataFrame with same structure
    
    # Get potential points
    potential_points = valid_df.loc[potential_hits].copy()
    
    # Filter to actual buffer using precise geometry
    in_buffer_mask = potential_points.apply(
        lambda row: buffer_geom.contains(Point(row[lon_col], row[lat_col])), 
        axis=1
    )
    
    return potential_points[in_buffer_mask]


def batch_spatial_query(center_points, spatial_index, valid_df, buffer_meters,
                       lat_col='LAT', lon_col='LON', progress_callback=None):
    """
    Perform spatial queries for multiple center points
    
    Args:
        center_points: DataFrame with center coordinates
        spatial_index: rtree Index object
        valid_df: DataFrame with indexed points
        buffer_meters: Buffer radius in meters
        lat_col: Latitude column name
        lon_col: Longitude column name
        progress_callback: Optional function to call with progress updates
        
    Returns:
        Dictionary mapping center point index to list of points in buffer
    """
    results = {}
    
    for i, (idx, row) in enumerate(center_points.iterrows()):
        if progress_callback and i % 100 == 0:
            progress_callback(i, len(center_points))
        
        points_in_buffer = query_spatial_index_with_buffer(
            spatial_index, row[lat_col], row[lon_col], buffer_meters, 
            valid_df, lat_col, lon_col
        )
        
        results[idx] = points_in_buffer
    
    return results








