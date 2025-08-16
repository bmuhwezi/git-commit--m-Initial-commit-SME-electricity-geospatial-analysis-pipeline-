#!/usr/bin/env python3
"""
File handling utilities
"""

import pickle
import pandas as pd
import os
from pathlib import Path


def load_pickle(filepath):
    """Load data from pickle file"""
    with open(filepath, 'rb') as f:
        return pickle.load(f)


def save_pickle(data, filepath):
    """Save data to pickle file"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)


def create_directories(dir_list):
    """Create directories if they don't exist"""
    for directory in dir_list:
        Path(directory).mkdir(parents=True, exist_ok=True)


def load_data(filepath, **kwargs):
    """Load data based on file extension"""
    if filepath.endswith('.pck'):
        return load_pickle(filepath)
    elif filepath.endswith('.csv'):
        return pd.read_csv(filepath, **kwargs)
    else:
        raise ValueError(f"Unsupported file type: {filepath}")


def save_data(data, filepath, **kwargs):
    """Save data based on file extension"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    if filepath.endswith('.pck'):
        save_pickle(data, filepath)
    elif filepath.endswith('.csv'):
        data.to_csv(filepath, index=False, **kwargs)
    else:
        raise ValueError(f"Unsupported file type: {filepath}")

def combine_chunk_results(base_path, num_chunks, output_filename):
    """
    Combine results from multiple chunks into single file
    
    Args:
        base_path: Base path pattern for chunk files (e.g., "SC_roads_distances_")
        num_chunks: Number of chunks to combine
        output_filename: Output filename for combined results
    """
    combined_data = []
    
    for chunk_id in range(num_chunks):
        chunk_file = f"{base_path}{chunk_id}.pck"
        if os.path.exists(chunk_file):
            chunk_data = load_pickle(chunk_file)
            combined_data.append(chunk_data)
        else:
            print(f"Warning: Chunk file {chunk_file} not found")
    
    if combined_data:
        result = pd.concat(combined_data, ignore_index=True)
        save_pickle(result, output_filename)
        print(f"Combined {len(combined_data)} chunks into {output_filename}")
        return result
    else:
        print("No chunk files found to combine")
        return None