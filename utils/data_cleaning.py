#!/usr/bin/env python3
"""
Data cleaning utilities for A2 and bills data
"""

import pandas as pd
import numpy as np


def clean_a2_data(a2_locs):
    """Clean A2 locations data"""
    # Remove rows with missing coordinates
    clean_data = a2_locs[~a2_locs[['LAT', 'LON']].isna().any(1)].copy()
    
    # Ensure NIS_RAD is present
    if 'NIS_RAD' not in clean_data.columns and 'nis_rad' in clean_data.columns:
        clean_data['NIS_RAD'] = clean_data['nis_rad']
    
    return clean_data


def clean_bills_data(a2_bills):
    """Clean A2 bills data"""
    # Remove duplicates
    clean_bills = a2_bills.drop_duplicates().copy()
    
    # Convert date columns
    if 'f_fact' in clean_bills.columns:
        clean_bills['f_fact'] = pd.to_datetime(clean_bills['f_fact'], dayfirst=True)
    
    if 'period' in clean_bills.columns:
        clean_bills['period'] = pd.to_datetime(clean_bills['period']).dt.to_period('M')
    
    # Remove extreme outliers (top 5%)
    if 'csmo_fact' in clean_bills.columns:
        q95 = clean_bills['csmo_fact'].quantile(0.95)
        clean_bills = clean_bills[clean_bills['csmo_fact'] <= q95]
    
    return clean_bills


def add_time_since_connection(bills_data, locations_data):
    """Add months since connection to bills data"""
    # Merge installation dates
    bills_with_install = bills_data.merge(
        locations_data[['NIS_RAD', 'installation']], 
        left_on='nis_rad', 
        right_on='NIS_RAD', 
        how='left'
    )
    
    # Convert installation date
    bills_with_install['installation'] = pd.to_datetime(
        bills_with_install['installation'], dayfirst=True
    )
    
    # Calculate months since connection
    bills_with_install['months_since_connection'] = (
        (bills_with_install['f_fact'] - bills_with_install['installation']) 
        / np.timedelta64(1, 'M')
    ).astype(int)
    
    return bills_with_install
