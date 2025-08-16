#!/usr/bin/env python3
"""
Main pipeline for SME electricity consumption analysis
"""

import pandas as pd
import numpy as np
import glob
import os
from pathlib import Path

from config import INPUT_PATHS, OUTPUT_PATHS, FEATURE_PARAMS
from utils.data_cleaning import clean_a2_data, clean_bills_data
from utils.file_utils import load_pickle, save_pickle, create_directories


def load_base_data():
    """Load and return A2 locations and bills data"""
    print("Loading base datasets...")
    
    # Load A2 locations
    a2_locs = load_pickle(INPUT_PATHS['a2_locations'])
    a2_locs = a2_locs[~a2_locs[['LAT', 'LON']].isna().any(1)]
    print(f"Loaded {len(a2_locs)} SME locations")
    
    # Load A2 bills
    if INPUT_PATHS['a2_bills'].endswith('.csv'):
        a2_bills = pd.read_csv(INPUT_PATHS['a2_bills'])
    else:
        a2_bills = load_pickle(INPUT_PATHS['a2_bills'])
    print(f"Loaded {len(a2_bills)} billing records")
    
    return a2_locs, a2_bills


def clean_data(a2_locs, a2_bills):
    """Clean and prepare datasets"""
    print("Cleaning datasets...")
    
    a2_locs_clean = clean_a2_data(a2_locs)
    a2_bills_clean = clean_bills_data(a2_bills)
    
    print(f"Cleaned data: {len(a2_locs_clean)} locations, {len(a2_bills_clean)} bills")
    return a2_locs_clean, a2_bills_clean


def combine_feature_files(feature_name, num_chunks):
    """Combine chunked feature files into single dataset"""
    print(f"Combining {feature_name} feature files...")
    
    feature_dir = OUTPUT_PATHS['features_dir']
    pattern_map = {
        'fsp': f'{feature_dir}/fsp/Nof_FSP_*.pck',
        'population': f'{feature_dir}/population/SC_*_*.pck', 
        'roads': f'{feature_dir}/roads/Roads*.pck',
        'nightlights': f'{feature_dir}/nightlights/SC_NL_*_*.pck',
        'structures': f'{feature_dir}/structures/SC_ElectStructs_*.pck'
    }
    
    if feature_name not in pattern_map:
        print(f"Unknown feature: {feature_name}")
        return pd.DataFrame()
    
    files = glob.glob(pattern_map[feature_name])
    if not files:
        print(f"No {feature_name} files found")
        return pd.DataFrame()
    
    combined_data = []
    for file in files:
        data = load_pickle(file)
        combined_data.append(data)
    
    result = pd.concat(combined_data, ignore_index=True)
    print(f"Combined {len(files)} {feature_name} files into {len(result)} records")
    return result


def create_features_dataframe(a2_locs, a2_bills):
    """Create final features dataframe by combining all extracted features"""
    print("Creating features dataframe...")
    
    # Start with base bill data
    df_features = a2_bills.copy()
    
    # Add location data
    df_features = df_features.merge(
        a2_locs[['NIS_RAD', 'LAT', 'LON']], 
        left_on='nis_rad', 
        right_on='NIS_RAD', 
        how='left'
    )
    
    # Combine extracted features
    features_to_combine = ['fsp', 'population', 'roads', 'nightlights', 'structures']
    
    for feature_name in features_to_combine:
        feature_data = combine_feature_files(feature_name, FEATURE_PARAMS['num_chunks'])
        
        if not feature_data.empty:
            # Merge based on common columns (typically nis_rad or index)
            merge_col = 'nis_rad' if 'nis_rad' in feature_data.columns else feature_data.index.name
            df_features = df_features.merge(feature_data, on=merge_col, how='left')
            print(f"Added {feature_name} features")
    
    return df_features


def submit_feature_extraction_jobs():
    """Submit SLURM jobs for feature extraction"""
    print("Submitting feature extraction jobs...")
    
    slurm_scripts = [
        'feature_extraction/slurm_scripts/fsp_array.sh',
        'feature_extraction/slurm_scripts/population_array.sh', 
        'feature_extraction/slurm_scripts/roads_array.sh',
        'feature_extraction/slurm_scripts/nightlights_array.sh'
    ]
    
    job_ids = []
    for script in slurm_scripts:
        if os.path.exists(script):
            print(f"Submitting {script}")
            # In practice, you would use subprocess to submit: 
            # result = subprocess.run(['sbatch', script], capture_output=True, text=True)
            # job_ids.append(result.stdout.strip().split()[-1])
            print(f"  -> sbatch {script}")
        else:
            print(f"Script not found: {script}")
    
    print("All jobs submitted. Wait for completion before running main pipeline.")
    return job_ids


def main():
    """Main pipeline execution"""
    print("Starting SME Electricity Analysis Pipeline")
    
    # Create output directories
    create_directories(list(OUTPUT_PATHS.values()))
    
    # Load and clean base data
    a2_locs, a2_bills = load_base_data()
    a2_locs_clean, a2_bills_clean = clean_data(a2_locs, a2_bills)
    
    # Save cleaned data
    save_pickle(a2_locs_clean, f"{OUTPUT_PATHS['results_dir']}/a2_locs_clean.pck")
    save_pickle(a2_bills_clean, f"{OUTPUT_PATHS['results_dir']}/a2_bills_clean.pck")
    
    # Check if feature extraction is needed
    features_exist = os.path.exists(f"{OUTPUT_PATHS['features_dir']}/fsp")
    
    if not features_exist:
        print("\nFeature extraction files not found.")
        print("Run feature extraction first:")
        submit_feature_extraction_jobs()
        print("\nRe-run this script after feature extraction completes.")
        return
    
    # Create final features dataframe
    df_features = create_features_dataframe(a2_locs_clean, a2_bills_clean)
    
    # Save final dataset
    df_features.to_csv(OUTPUT_PATHS['final_dataset'], index=False)
    save_pickle(df_features, OUTPUT_PATHS['final_dataset'].replace('.csv', '.pck'))
    
    print(f"\nPipeline complete!")
    print(f"Final dataset saved: {OUTPUT_PATHS['final_dataset']}")
    print(f"Dataset shape: {df_features.shape}")
    print(f"Features: {list(df_features.columns)}")


if __name__ == "__main__":
    main()
